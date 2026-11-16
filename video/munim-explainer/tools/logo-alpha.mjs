// Cut the Munim mark out of munim-logo.png: unmix from white (alpha from saturation, edges unmixed from white), drop the stray left edge line, crop tight.
import {spawnSync} from 'node:child_process';
const [src,dest]=process.argv.slice(2);const W=465,H=462,M=24;
const raw=spawnSync('ffmpeg',['-v','error','-i',src,'-f','rawvideo','-pix_fmt','rgba','-'],{maxBuffer:1<<26}).stdout;
const out=Buffer.alloc(raw.length);let x0=W,y0=H,x1=0,y1=0;
for(let y=0;y<H;y++)for(let x=0;x<W;x++){const i=(y*W+x)*4,r=raw[i],g=raw[i+1],b=raw[i+2];
 const sat=Math.max(r,g,b)-Math.min(r,g,b);let a=x<20?0:Math.min(1,Math.max(0,(sat-10)/70));
 if(a>0){const un=c=>Math.round(Math.min(255,Math.max(0,(c-(1-a)*255)/a)));out[i]=un(r);out[i+1]=un(g);out[i+2]=un(b);out[i+3]=Math.round(a*255);
  if(a>.5){x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}}}
const cx=x0-M,cy=y0-M,cw=x1-x0+1+2*M,ch=y1-y0+1+2*M;
const r=spawnSync('ffmpeg',['-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',`${W}x${H}`,'-i','-','-vf',`crop=${cw}:${ch}:${cx}:${cy}`,dest],{input:out});
if(r.status)throw Error(r.stderr.toString());console.log('mark bbox',x0,y0,x1,y1,'->',cw+'x'+ch);
