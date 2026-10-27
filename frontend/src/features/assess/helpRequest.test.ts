import {describe,it,expect} from 'vitest'
import {isHelpRequest} from './helpRequest'
describe('explicit uncertainty before checking',()=>{
 it.each(["I don't know", " I DON’T KNOW! ", 'idk', 'Ich weiß es nicht.', 'keine Ahnung', 'not sure'])('offers help for %s',answer=>expect(isHelpRequest(answer)).toBe(true))
 it.each(['42','no','SELECT','I do not know whether the policy matches, but SELECT needs a grant.','Eine Rolle braucht SELECT.'])('keeps substantive and short answers checkable: %s',answer=>expect(isHelpRequest(answer)).toBe(false))
})
