// Capture real Munim UI screens for the film (dev server must be running).
import {capturePage} from './node_modules/@launch-video-maker/runtime/runtime/dist/tools.js';
const base=process.argv[2]??'http://localhost:5174';
const skip=async page=>{const b=page.getByRole('button',{name:'Skip setup'});if(await b.isVisible({timeout:4000}).catch(()=>false))await b.click();await page.waitForTimeout(800);};
for(const [name,path] of [['dashboard','/dashboard'],['assistant','/chat'],['documents','/documents']]){
 const r=await capturePage(base+'/dashboard',`assets/ui/${name}`,[],async page=>{await skip(page);if(path!=='/dashboard'){await page.goto(base+path,{waitUntil:'load'});await skip(page);}});
 console.log(name,r.finalURL);
}
