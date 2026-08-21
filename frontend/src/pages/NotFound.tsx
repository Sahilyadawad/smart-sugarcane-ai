import { Link } from 'react-router-dom'
import { Home, Sprout } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="grid min-h-screen place-items-center px-6 text-center">
      <div>
        <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-cane-100 text-cane-700 dark:bg-cane-950 dark:text-cane-300">
          <Sprout className="size-8" />
        </span>
        <h1 className="mt-6 font-display text-5xl font-extrabold">404</h1>
        <p className="mt-3 text-lg font-semibold">This page does not exist</p>
        <p className="mx-auto mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
          The link may be out of date, or the address may have a typo in it.
        </p>
        <Link to="/" className="btn-primary mt-8">
          <Home className="size-4" />
          Back to home
        </Link>
      </div>
    </div>
  )
}
