// Render stage-1 direction frames (assets/directions/src/*.html) to 1920x1080 PNGs.
import {chromium} from 'playwright';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const browser=await chromium.launch();
try{
 const page=await browser.newPage({viewport:{width:1920,height:1080}});
 for(const id of ['a','b','c']){
  await page.goto(pathToFileURL(resolve(`assets/directions/src/${id}.html`)).href,{waitUntil:'networkidle'});
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:`assets/directions/${id}.png`});console.log(id,'ok');
 }
}finally{await browser.close();}
