import {Link} from 'react-router-dom'
import {Card,CardTitle} from '../components/ui/card'
export function Library(){return <div className="grid gap-4">
 <h1 className="text-page-title font-semibold">Library</h1>
 <p>Create your material, return to saved work, or find a source.</p>
 <Link className="inline-flex min-h-11 items-center underline font-semibold" to="/curriculum">Create or continue knowledge material</Link>
 <Card><CardTitle as="h2">My material</CardTitle><ul className="grid gap-3 mt-3">
 <li><Link className="inline-flex min-h-11 items-center underline" to="/answers">Saved answers</Link></li>
 </ul></Card>
 <Card><CardTitle as="h2">Find and import</CardTitle><ul className="grid gap-3 mt-3">
 <li><Link className="inline-flex min-h-11 items-center underline" to="/search">Search material</Link></li>
 <li><Link className="inline-flex min-h-11 items-center underline" to="/sources">Browse source passages</Link></li>
 <li><Link className="inline-flex min-h-11 items-center underline" to="/corpus">Import and manage source files</Link></li>
 </ul></Card>
 <details><summary className="cursor-pointer">More library views</summary><ul className="grid gap-3 mt-3">
 <li><Link className="inline-flex min-h-11 items-center underline" to="/areas">Learning areas</Link></li>
 <li><Link className="inline-flex min-h-11 items-center underline" to="/explore">Explore material by area</Link></li>
 </ul></details>
 </div>}
