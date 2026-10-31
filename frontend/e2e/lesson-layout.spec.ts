import {expect,test} from '@playwright/test'
import axe from 'axe-core'
import {API,endOpenSession,expectOk,currentSession} from './helpers'
for(const theme of ['light','dark']) for(const width of [320,390,1280]) test(`lesson leads before grouped tools ${width} ${theme}`,async({page,request},info)=>{
 await endOpenSession(request)
 try{
  await expectOk(await request.put(API+'/api/preferences',{data:{key:'ui.theme',value:theme}}))
  const res=await request.post(API+'/api/sessions',{data:{mode:'steady',energy:3}});await expectOk(res)
  const session=await res.json();const index=session.plan.findIndex((b:{type:string})=>b.type==='new_material')
  await expectOk(await request.post(API+'/api/plan/blocks/start',{data:{session_id:session.id,index}}))
  await page.setViewportSize({width,height:900});await page.goto('/');await page.getByRole('button',{name:'Continue',exact:true}).click()
  await expect(page.getByRole('heading',{name:'Your explanation',exact:true})).toBeVisible()
  const more=page.locator('summary').filter({hasText:/^More session tools$/})
  await expect(more).toBeVisible()
  await expect(page.getByRole('heading',{name:'Learning context',exact:true})).not.toBeVisible()
  const draft=page.getByLabel('Ask about this lesson (optional)');await draft.fill('Keep my question while toggling tools')
  const checkpoint=await currentSession(request)
  await more.focus();await page.keyboard.press('Enter')
  await expect(page.getByRole('heading',{name:'Learning context',exact:true})).toBeVisible()
  const plan=page.locator('summary').filter({hasText:/^Session plan and energy settings$/})
  await plan.click();await expect(page.getByRole('button',{name:'Energy 3',exact:true})).toBeVisible()
  await more.click();await expect(page.getByRole('button',{name:'Energy 3',exact:true})).not.toBeVisible()
  await expect(draft).toHaveValue('Keep my question while toggling tools')
  await more.click();await expect(page.getByRole('button',{name:'Energy 3',exact:true})).toBeVisible()
  const afterTools=await currentSession(request)
  if (!checkpoint || !afterTools) throw new Error('Open session disappeared while toggling tools')
  // Due reviews are computed from the current clock; every persisted session field must match.
  expect(afterTools).toEqual({...checkpoint,due_reviews:afterTools.due_reviews})
  await page.reload();await expect(draft).toHaveValue('Keep my question while toggling tools')
  await expect(page.getByRole('heading',{name:'Learning context',exact:true})).toBeVisible()
  await more.click()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
  await page.addScriptTag({content:axe.source});expect(await page.evaluate(async()=>(await (window as unknown as {axe:typeof axe}).axe.run('main')).violations)).toEqual([])
  await page.screenshot({path:info.outputPath('grouped-session.png'),fullPage:true})
 } finally {await endOpenSession(request)}
})
