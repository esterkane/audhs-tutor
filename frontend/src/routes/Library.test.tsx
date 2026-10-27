import {render,screen} from '@testing-library/react'
import {expect,it} from 'vitest'
import {MemoryRouter} from 'react-router-dom'
import {Library} from './Library'
it('groups authoring and sources without adding another global tools menu',()=>{
 render(<MemoryRouter><Library/></MemoryRouter>)
 expect(screen.getByRole('heading',{level:1,name:'Library'})).toBeVisible()
 expect(screen.getByRole('link',{name:'Create or continue knowledge material'})).toHaveAttribute('href','/curriculum')
 expect(screen.getByRole('link',{name:'Saved answers'})).toHaveAttribute('href','/answers')
 expect(screen.getByRole('link',{name:'Import and manage source files'})).toHaveAttribute('href','/corpus')
 expect(screen.queryByRole('button',{name:'Tools'})).toBeNull()
})
