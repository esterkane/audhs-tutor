import {expect,test} from '@playwright/test'
for(const width of [390,1280]) test(`Library keeps known results when refresh fails ${width}`,async({page},info)=>{
 await page.setViewportSize({width,height:900})
 let failing=false
 const fixtures:Record<string,unknown>={
 '**/api/curriculum/drafts':{drafts:[{id:'d',title:'Example draft',status:'draft',origin:'knowledge_authored',version:1,payload:{notes:'Example finding'}}]},
 '**/api/skills':{skills:[{id:'s',title:'Example lesson',description:'Example',unlocked:true,prerequisites:[],mastery:0,state:{}}]},
 '**/api/answers?*':{items:[{id:'a',request_text:'Example answer',preview:'Evidence',created_at:'2026-10-01',surface:'tutor'}],next_cursor:null},
 '**/api/corpus/search':{hits:[{chunk_id:'p',citation:'Example source',source_type:'text',text:'Evidence',flagged:[],quarantined:false}]},
 }
 const reads:Record<string,number>={}
 for(const [pattern,json] of Object.entries(fixtures)) await page.route(pattern,route=>{
 reads[pattern]=(reads[pattern]??0)+1;return route.fulfill(failing?{status:503,json:{}}:{json})
 })
 await page.goto('/search?q=example')
 await expect(page).toHaveURL(/\/library\?q=example$/)
 for(const name of ['Example draft','Example lesson','Example answer'])await expect(page.getByRole('link',{name,exact:true})).toBeVisible()
 const source=page.getByRole('button',{name:'Read passage: Example source',exact:true});await expect(source).toBeVisible()
 failing=true
 await page.getByRole('button',{name:'Search',exact:true}).click()
 await expect(page.getByRole('button',{name:'Retry source search',exact:true})).toBeVisible()
 await expect(page.getByRole('button',{name:'Retry material search',exact:true})).toBeEnabled()
 for(const name of ['Example draft','Example lesson','Example answer'])await expect(page.getByRole('link',{name,exact:true})).toBeVisible()
 await expect(source).toBeVisible()
 await expect(page.getByText('Showing previously loaded results; they may be out of date.',{exact:true})).toHaveCount(3)
 const before={...reads};failing=false
 await page.getByRole('button',{name:'Retry source search',exact:true}).click()
 await expect(page.getByRole('button',{name:'Retry source search',exact:true})).toHaveCount(0)
 for(const pattern of Object.keys(fixtures))expect(reads[pattern]).toBe(before[pattern]+(pattern==='**/api/corpus/search'?1:0))
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.screenshot({path:info.outputPath('library-cached-results.png'),fullPage:true})
})
