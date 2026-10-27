import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PlanStrip } from './PlanStrip'

describe('PlanStrip', () => {
  it('marks the current block and shows optional blocks honestly', () => {
    render(
      <PlanStrip
        current={1}
        blocks={[
          {
            type: 'movement_primer',
            planned_min: 5,
            optional: true,
            node_ids: [],
            reason: '',
            grasp_check_required: false,
          },
          {
            type: 'retrieval',
            planned_min: 7,
            optional: false,
            node_ids: [],
            reason: '',
            grasp_check_required: false,
          },
          {
            type: 'recap',
            planned_min: 5,
            optional: false,
            node_ids: [],
            reason: '',
            grasp_check_required: false,
          },
        ]}
      />,
    )
    const items = screen.getAllByRole('listitem')
    expect(items).toHaveLength(3)
    expect(items[0]).toHaveTextContent('Move · 5 min · optional')
    expect(items[1]).toHaveAttribute('aria-current', 'step')
    expect(items[2]).toHaveTextContent('Recap · 5 min')
  })
})


it('explains blocks passed over at the recorded start without marking them completed',()=>{
 render(<PlanStrip current={1} firstStarted={1} blocks={[
 {type:'movement_primer',planned_min:5,optional:true,node_ids:[],reason:'',grasp_check_required:false},
 {type:'new_material',planned_min:10,optional:false,node_ids:[],reason:'',grasp_check_required:true},
 ]}/>)
 const prior=screen.getAllByRole('listitem')[0]
 expect(prior).toHaveTextContent('skipped at start')
 expect(prior).not.toHaveClass('line-through')
})
