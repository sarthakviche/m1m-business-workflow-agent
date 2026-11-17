"""
Multi-tenant security tests: login verification, signup, and isolation.

These are the tests that let a second business on the platform. Two businesses
sign up through the real API with real signed tokens, and each tries to reach
the other's data. The route sweep also fails when someone adds a new endpoint
that doesn't require credentials.
"""

from __future__ import annotations

import shutil
import time
import uuid
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx
import jwt
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.auth.dependencies as auth_dependencies
from app.api.v1 import account as account_api
from app.api.v1.documents import _DOCS_ROOT
from app.auth.tenant_resolver import TenantResolver
from app.auth.tokens import TokenVerifier
from app.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app as fastapi_app
from app.models.customer import Customer
from app.models.item import Item
from app.models.quotation import Quotation
from app.models.stock import Stock
from app.services.catalog_service import list_catalog_summary, lookup_catalog_item_details
from app.services.customer_lookup import lookup_customer_scored
from app.services.document_lookup import find_document_by_number, list_recent_documents
from app.services.invoice_service import QuotationNotFoundError, convert_quotation_to_invoice
from app.services.item_lookup import lookup_item

SECRET = "test-signing-secret-that-is-long-enough-for-hs256"
ISSUER = "https://example.supabase.co/auth/v1"
AUDIENCE = "authenticated"


def make_token(subject: str, *, secret: str = SECRET, algorithm: str = "HS256", **overrides) -> str:
    claims = {
        "sub": subject,
        "aud": AUDIENCE,
        "iss": ISSUER,
        "exp": int(time.time()) + 3600,
        "email": f"{subject}@example.com",
    }
    claims.update(overrides)
    return jwt.encode(claims, secret, algorithm=algorithm)


def bearer(subject: str) -> dict:
    return {"Authorization": f"Bearer {make_token(subject)}"}


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    main_url = get_settings().async_database_url
    if main_url.startswith("sqlite"):
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tenants.db'}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        # The disposable Postgres, already migrated. Tests reuse the same login names.
        engine = create_async_engine(main_url)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM app_user"))
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory, monkeypatch):
    """An API client behaving like production: no dev fallback, tokens required."""
    verifier = TokenVerifier(audience=AUDIENCE, issuer=ISSUER, hs256_secret=SECRET)
    resolver = TenantResolver(key_map={}, dev_tenant_id=None, is_dev=False)
    monkeypatch.setattr(auth_dependencies, "get_token_verifier", lambda: verifier)
    monkeypatch.setattr(auth_dependencies, "get_tenant_resolver", lambda: resolver)
    monkeypatch.setattr(account_api, "get_tenant_resolver", lambda: resolver)

    async def override_session():
        async with session_factory() as session:
            yield session
            await session.commit()

    fastapi_app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    fastapi_app.dependency_overrides.clear()


async def sign_up(http, subject: str, name: str, state: str = "Maharashtra") -> str:
    response = await http.post(
        "/api/v1/business",
        json={"business_name": name, "state": state},
        headers=bearer(subject),
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest_asyncio.fixture
async def two_businesses(client, session_factory):
    """Alice and Bob each own a business with a customer, an item, a stock row and a quotation."""
    alice_id = await sign_up(client, "alice", "Alice Traders")
    bob_id = await sign_up(client, "bob", "Bob Hardware", state="Gujarat")

    async with session_factory() as s:
        for tenant, customer_name, item_name, number in (
            (alice_id, "Alice Customer", "Alice Cement", "Q-A-1"),
            (bob_id, "Bob Customer", "Bob Paint", "Q-B-1"),
        ):
            tenant_id = uuid.UUID(tenant)
            customer = Customer(tenant_id=tenant_id, name=customer_name, state="Maharashtra")
            item = Item(tenant_id=tenant_id, name=item_name, gst_rate_percent=Decimal("18"),
                        unit_price=Decimal("100"), unit="pcs", hsn_code="2523")
            s.add_all([customer, item])
            await s.flush()
            s.add_all([
                Stock(item_id=item.id, tenant_id=tenant_id, quantity_available=Decimal("50")),
                Quotation(tenant_id=tenant_id, customer_id=customer.id, quotation_number=number,
                          status="draft", subtotal=Decimal("100"),
                          pdf_url=f"/documents/{tenant}/quotations/{number}.pdf"),
            ])
        await s.commit()

    yield {"alice": alice_id, "bob": bob_id}
    for tenant in (alice_id, bob_id):
        shutil.rmtree(_DOCS_ROOT / tenant, ignore_errors=True)


# ── Token verification ───────────────────────────────────────────────────────


@pytest.fixture
def verifier():
    return TokenVerifier(audience=AUDIENCE, issuer=ISSUER, hs256_secret=SECRET)


async def test_valid_token_gives_a_principal(verifier):
    token = make_token("u1", user_metadata={"full_name": "Asha Rao"})
    principal = await verifier.verify(token)
    assert (principal.subject, principal.email, principal.name) == ("u1", "u1@example.com", "Asha Rao")


@pytest.mark.parametrize("token_factory", [
    pytest.param(lambda: make_token("u1", secret="x" * 40), id="wrong-signature"),
    pytest.param(lambda: make_token("u1", exp=int(time.time()) - 3600), id="expired"),
    pytest.param(lambda: make_token("u1", aud="anon"), id="wrong-audience"),
    pytest.param(lambda: make_token("u1", iss="https://evil.example/auth/v1"), id="wrong-issuer"),
    pytest.param(lambda: make_token("u1", is_anonymous=True), id="anonymous-session"),
    pytest.param(lambda: jwt.encode({"sub": "u1", "aud": AUDIENCE, "iss": ISSUER, "exp": int(time.time()) + 60},
                                    None, algorithm="none"), id="alg-none"),
    pytest.param(lambda: jwt.encode({"sub": "u1", "aud": AUDIENCE, "iss": ISSUER, "exp": int(time.time()) + 60},
                                    ec.generate_private_key(ec.SECP256R1()), algorithm="ES256"),
                 id="asymmetric-without-jwks"),
    pytest.param(lambda: jwt.encode({"aud": AUDIENCE, "iss": ISSUER, "exp": int(time.time()) + 60},
                                    SECRET, algorithm="HS256"), id="missing-subject"),
    pytest.param(lambda: "not-a-jwt", id="garbage"),
])
async def test_bad_tokens_are_rejected(verifier, token_factory):
    from app.errors.categories import AuthenticationError
    with pytest.raises(AuthenticationError):
        await verifier.verify(token_factory())


class _FakeJwks:
    """Stands in for the project's JWKS endpoint, which is how Supabase signs tokens today (ES256)."""

    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key_from_jwt(self, _token):
        return SimpleNamespace(key=self.public_key)


def _es256_claims(**overrides):
    return {"sub": "u1", "aud": AUDIENCE, "iss": ISSUER, "exp": int(time.time()) + 60, **overrides}


async def test_es256_tokens_verify_against_the_published_key():
    private = ec.generate_private_key(ec.SECP256R1())
    verifier = TokenVerifier(audience=AUDIENCE, issuer=ISSUER, jwks_client=_FakeJwks(private.public_key()))
    principal = await verifier.verify(jwt.encode(_es256_claims(), private, algorithm="ES256"))
    assert principal.subject == "u1"


async def test_es256_token_signed_by_anyone_else_is_rejected():
    from app.errors.categories import AuthenticationError
    published = ec.generate_private_key(ec.SECP256R1()).public_key()
    verifier = TokenVerifier(audience=AUDIENCE, issuer=ISSUER, jwks_client=_FakeJwks(published))
    with pytest.raises(AuthenticationError):
        await verifier.verify(jwt.encode(_es256_claims(), ec.generate_private_key(ec.SECP256R1()), algorithm="ES256"))


async def test_hs256_token_is_refused_when_only_asymmetric_keys_are_configured():
    """Algorithm confusion: an attacker signs HS256 using the public key as the secret."""
    from app.errors.categories import AuthenticationError
    verifier = TokenVerifier(audience=AUDIENCE, issuer=ISSUER,
                             jwks_client=_FakeJwks(ec.generate_private_key(ec.SECP256R1()).public_key()))
    with pytest.raises(AuthenticationError):
        await verifier.verify(make_token("u1", secret="x" * 40))


async def test_bad_token_never_falls_through_to_the_dev_tenant(client, monkeypatch):
    """Even in dev mode, a token that fails verification is a 401, not the demo business."""
    dev = TenantResolver(key_map={}, dev_tenant_id=uuid.uuid4(), is_dev=True)
    monkeypatch.setattr(auth_dependencies, "get_tenant_resolver", lambda: dev)
    response = await client.get("/api/v1/customers", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


# ── Signup and onboarding ────────────────────────────────────────────────────


async def test_new_login_has_no_business_until_it_creates_one(client):
    me = (await client.get("/api/v1/me", headers=bearer("newbie"))).json()
    assert me["email"] == "newbie@example.com"
    assert me["business"] is None

    blocked = await client.get("/api/v1/customers", headers=bearer("newbie"))
    assert blocked.status_code == 403
    assert blocked.json()["error_code"] == "business_required"

    await sign_up(client, "newbie", "Newbie Traders")
    me = (await client.get("/api/v1/me", headers=bearer("newbie"))).json()
    assert me["business"]["business_name"] == "Newbie Traders"
    assert me["business"]["onboarded"] is False
    assert me["role"] == "owner"


async def test_onboarding_state_lives_on_the_server(client):
    await sign_up(client, "owner", "Owner Co")
    done = await client.post("/api/v1/business/complete-onboarding", headers=bearer("owner"))
    assert done.json()["onboarded"] is True
    # A fresh device sees the same state.
    me = (await client.get("/api/v1/me", headers=bearer("owner"))).json()
    assert me["business"]["onboarded"] is True


async def test_second_business_on_one_login_is_refused(client):
    await sign_up(client, "owner", "First Co")
    again = await client.post("/api/v1/business", json={"business_name": "Second Co", "state": "Goa"},
                              headers=bearer("owner"))
    assert again.status_code == 409


async def test_signup_validates_the_gstin(client):
    response = await client.post("/api/v1/business",
                                 json={"business_name": "Co", "state": "Goa", "gstin": "nonsense"},
                                 headers=bearer("owner"))
    assert response.status_code == 422


async def test_signup_cannot_choose_its_tenant_id(client):
    forced = str(uuid.uuid4())
    response = await client.post("/api/v1/business",
                                 json={"id": forced, "tenant_id": forced, "business_name": "Co", "state": "Goa"},
                                 headers=bearer("owner"))
    assert response.status_code == 201
    assert response.json()["id"] != forced


# ── Every endpoint requires credentials ──────────────────────────────────────

# Public by design. Adding to this list should be a conscious security decision.
PUBLIC_ROUTES = {"/health", "/ready", "/api/v1/telegram/webhook"}


def _protected_routes() -> list[tuple[str, str]]:
    # From the OpenAPI schema, because app.routes doesn't expose included routers directly.
    routes = sorted(
        (method.upper(), path)
        for path, operations in fastapi_app.openapi()["paths"].items()
        if path not in PUBLIC_ROUTES
        for method in operations
        if method.upper() not in {"HEAD", "OPTIONS"}
    )
    # An empty list would silently skip the sweep below and protect nothing.
    assert len(routes) >= 12, f"Route discovery looks broken: {routes}"
    return routes


@pytest.mark.parametrize("method,path", _protected_routes())
async def test_every_route_rejects_anonymous_callers(client, method, path):
    url = path.replace("{tenant_id}", str(uuid.uuid4())).replace("{doc_type}", "invoices").replace("{filename}", "x.pdf")
    response = await client.request(method, url, json={})
    assert response.status_code == 401, f"{method} {path} is reachable without credentials"


# ── Isolation between businesses ─────────────────────────────────────────────


async def test_list_endpoints_show_only_your_own_data(client, two_businesses):
    for path, field, own, other in (
        ("/api/v1/customers", "name", "Alice Customer", "Bob Customer"),
        ("/api/v1/items", "name", "Alice Cement", "Bob Paint"),
    ):
        names = {row[field] for row in (await client.get(path, headers=bearer("alice"))).json()}
        assert own in names and other not in names

    docs = (await client.get("/api/v1/documents", headers=bearer("alice"))).json()["documents"]
    assert {d["document_number"] for d in docs} == {"Q-A-1"}

    dash = (await client.get("/api/v1/dashboard/summary", headers=bearer("alice"))).json()
    assert dash["total_customers"] == 1
    assert {d["document_number"] for d in dash["recent_documents"]} == {"Q-A-1"}


async def test_business_profile_edits_stay_in_your_business(client, two_businesses):
    await client.patch("/api/v1/business", json={"business_name": "Renamed"}, headers=bearer("alice"))
    assert (await client.get("/api/v1/business", headers=bearer("alice"))).json()["business_name"] == "Renamed"
    assert (await client.get("/api/v1/business", headers=bearer("bob"))).json()["business_name"] == "Bob Hardware"


async def test_pdfs_are_only_served_to_their_owner(client, two_businesses):
    folder = _DOCS_ROOT / two_businesses["bob"] / "quotations"
    folder.mkdir(parents=True)
    (folder / "Q-B-1.pdf").write_bytes(b"%PDF-1.4 bob's invoice")
    url = f"/documents/{two_businesses['bob']}/quotations/Q-B-1.pdf"

    assert (await client.get(url, headers=bearer("bob"))).status_code == 200
    assert (await client.get(url)).status_code == 401
    # 404, not 403: never confirm that another business's document exists.
    assert (await client.get(url, headers=bearer("alice"))).status_code == 404


async def test_pdf_path_cannot_climb_into_another_tenant(client, two_businesses):
    folder = _DOCS_ROOT / two_businesses["bob"] / "quotations"
    folder.mkdir(parents=True)
    (folder / "Q-B-1.pdf").write_bytes(b"%PDF-1.4 bob's invoice")
    alice = two_businesses["alice"]
    response = await client.get(
        f"/documents/{alice}/..%2F..%2F{two_businesses['bob']}%2Fquotations/Q-B-1.pdf",
        headers=bearer("alice"),
    )
    assert response.status_code in (400, 404)
    assert b"bob's invoice" not in response.content


async def test_catalog_import_writes_only_to_your_business(client, two_businesses):
    rows = [{"name": "Bob Paint", "unit_price": "1", "unit": "pcs", "hsn_code": None, "gst_rate_percent": "18"}]
    response = await client.post("/api/v1/catalog/import", json={"items": rows}, headers=bearer("alice"))
    assert response.json()["created"] == 1  # a new item for Alice, not an update of Bob's

    bob_items = {i["name"]: i for i in (await client.get("/api/v1/items", headers=bearer("bob"))).json()}
    assert bob_items["Bob Paint"]["unit_price"] == 100.0


async def test_assistant_cannot_see_another_business(client, two_businesses):
    """The same request succeeds with Alice's own item and fails with Bob's."""
    own = await client.post(
        "/api/v1/chat",
        json={"message": "create quotation for Asha Stores for 5 units Alice Cement"},
        headers=bearer("alice"),
    )
    assert own.json()["document_number"], "control: this phrasing must create a document"

    other = await client.post(
        "/api/v1/chat",
        json={"message": "create quotation for Asha Stores for 5 units Bob Paint"},
        headers=bearer("alice"),
    )
    assert other.status_code == 200
    assert other.json()["document_number"] is None

    price = await client.post("/api/v1/chat", json={"message": "what is the price of Bob Paint"}, headers=bearer("alice"))
    assert "100" not in price.json()["response_text"]

    # Nothing leaked into Bob's business either.
    customers = {c["name"] for c in (await client.get("/api/v1/customers", headers=bearer("bob"))).json()}
    assert customers == {"Bob Customer"}
    docs = (await client.get("/api/v1/documents", headers=bearer("bob"))).json()["documents"]
    assert {d["document_number"] for d in docs} == {"Q-B-1"}


async def test_services_only_search_the_given_business(session_factory, two_businesses):
    """The lookups behind the assistant and Telegram, including when both businesses share a name."""
    alice, bob = uuid.UUID(two_businesses["alice"]), uuid.UUID(two_businesses["bob"])

    async with session_factory() as s:
        assert await lookup_item(s, alice, "Bob Paint") is None
        assert (await lookup_item(s, bob, "Bob Paint")).tenant_id == bob

        match = await lookup_customer_scored(s, alice, "Bob Customer")
        assert match.customer is None or match.customer.tenant_id == alice
        assert (await lookup_customer_scored(s, bob, "Bob Customer")).customer.tenant_id == bob

        assert (await lookup_catalog_item_details(s, alice, "Bob Paint"))["found"] is False
        names = [i["name"] for i in (await list_catalog_summary(s, alice))["displayed_items"]]
        assert names == ["Alice Cement"]

        assert await find_document_by_number(s, alice, "Q-B-1") is None
        assert (await find_document_by_number(s, bob, "Q-B-1")).number == "Q-B-1"
        assert [d.number for d in await list_recent_documents(s, alice, "quotation")] == ["Q-A-1"]

        # Same item and customer names in two businesses must not cross over.
        s.add_all([
            Item(tenant_id=alice, name="Bob Paint", gst_rate_percent=Decimal("5"), unit_price=Decimal("7"), unit="pcs"),
            Customer(tenant_id=alice, name="Bob Customer"),
        ])
        await s.flush()
        assert (await lookup_item(s, alice, "Bob Paint")).unit_price == Decimal("7")
        assert (await lookup_item(s, bob, "Bob Paint")).unit_price == Decimal("100")
        assert (await lookup_customer_scored(s, alice, "Bob Customer")).customer.tenant_id == alice
        await s.rollback()


async def test_cannot_convert_another_business_quotation(client, two_businesses):
    response = await client.post(
        "/api/v1/chat",
        json={"message": "convert quotation Q-B-1 into an invoice"},
        headers=bearer("alice"),
    )
    assert response.status_code == 200
    assert response.json()["document_number"] is None
    docs = (await client.get("/api/v1/documents", headers=bearer("bob"))).json()["documents"]
    assert {(d["document_number"], d["status"]) for d in docs} == {("Q-B-1", "draft")}


async def test_service_refuses_another_business_quotation(session_factory, two_businesses):
    alice = uuid.UUID(two_businesses["alice"])
    async with session_factory() as s:
        with pytest.raises(QuotationNotFoundError):
            await convert_quotation_to_invoice(s, alice, "Q-B-1")


async def test_new_business_can_issue_its_first_document(client):
    """The whole journey for a stranger: signup, catalog, quotation, PDF."""
    tenant_id = await sign_up(client, "fresh", "Fresh Traders")
    auth = bearer("fresh")
    try:
        imported = await client.post("/api/v1/catalog/import", headers=auth, json={"items": [
            {"name": "Steel Rod 12mm", "unit_price": "68.50", "unit": "kg", "hsn_code": "7214",
             "gst_rate_percent": "18", "quantity_available": "500"},
        ]})
        assert imported.json()["created"] == 1

        chat = await client.post("/api/v1/chat", headers=auth, json={
            "message": "create quotation for Ramesh Traders for 10 units Steel Rod 12mm",
        })
        body = chat.json()
        assert body["document_number"], body
        assert body["pdf_url"].startswith(f"/documents/{tenant_id}/")

        pdf = await client.get(body["pdf_url"], headers=auth)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
    finally:
        shutil.rmtree(_DOCS_ROOT / tenant_id, ignore_errors=True)


# ── Fail-closed configuration ────────────────────────────────────────────────


def test_missing_env_means_production(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    assert Settings(_env_file=None).is_development is False


def _prod_settings(**overrides) -> Settings:
    values = {
        "env": "production",
        "database_url": "postgresql://u:p@db.example.com/x",
        "supabase_url": "https://x.supabase.co",
        "cors_origins": "https://app.example.com",
        "telegram_bot_token": "",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_safe_production_config_has_no_problems():
    assert _prod_settings().production_config_problems() == []


@pytest.mark.parametrize("overrides,expected", [
    ({"database_url": "sqlite+aiosqlite:///x.db"}, "DATABASE_URL"),
    ({"supabase_url": "", "supabase_jwt_secret": ""}, "SUPABASE_URL"),
    ({"cors_origins": "*"}, "CORS_ORIGINS"),
    ({"cors_origins": "http://localhost:5173"}, "CORS_ORIGINS"),
    ({"telegram_bot_token": "abc", "telegram_webhook_secret": ""}, "TELEGRAM_WEBHOOK_SECRET"),
])
def test_unsafe_production_config_is_caught(overrides, expected):
    problems = _prod_settings(**overrides).production_config_problems()
    assert any(expected in p for p in problems)


def test_problem_messages_never_contain_secrets():
    problems = _prod_settings(database_url="sqlite+aiosqlite:///hunter2.db",
                              telegram_bot_token="tok3n", telegram_webhook_secret="").production_config_problems()
    assert problems
    assert "hunter2" not in " ".join(problems) and "tok3n" not in " ".join(problems)


async def test_app_refuses_to_start_with_unsafe_config(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(main_module, "settings", _prod_settings(cors_origins="*"))
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        async with main_module.lifespan(fastapi_app):
            pass


# ── Operations ───────────────────────────────────────────────────────────────


async def test_health_and_ready(client):
    assert (await client.get("/health")).json()["status"] == "ok"
    assert (await client.get("/ready")).json() == {"status": "ok"}
    assert (await client.head("/ready")).status_code == 200


async def test_responses_carry_request_id_and_security_headers(client):
    response = await client.get("/health")
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    traced = await client.get("/health", headers={"X-Request-ID": "trace-12345"})
    assert traced.headers["X-Request-ID"] == "trace-12345"


async def test_unsafe_request_id_is_replaced(client):
    response = await client.get("/health", headers={"X-Request-ID": "bad id\twith junk"})
    assert "junk" not in response.headers["X-Request-ID"]


async def test_unexpected_errors_are_safe_json_with_cors(client, monkeypatch):
    async def explode(*_args, **_kwargs):
        raise RuntimeError("secret internal detail: postgres://u:p@host")

    monkeypatch.setattr(auth_dependencies, "find_user", explode)
    response = await client.get(
        "/api/v1/customers",
        headers={**bearer("alice"), "Origin": "http://localhost:5173"},
    )
    assert response.status_code == 500
    assert "secret" not in response.text
    assert response.json()["error_code"] == "internal_error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_preflight_allows_patch_with_authorization():
    from fastapi.testclient import TestClient
    response = TestClient(fastapi_app).options("/api/v1/business", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "PATCH",
        "Access-Control-Request-Headers": "authorization",
    })
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


def test_repo_ignores_local_databases_and_secrets():
    gitignore = (Path(__file__).resolve().parents[2] / ".gitignore").read_text(encoding="utf-8")
    assert "*.db" in gitignore and ".env" in gitignore
