import { AlertTriangle, CheckCircle2, Info, Leaf, Search, XCircle } from 'lucide-react'
import type { ImageValidation } from '../types'

/** Instruction shown above the upload control, before anything is chosen. */
export function UploadHint({ kind }: { kind: 'plant' | 'soil' }) {
  return (
    <div className="flex items-start gap-2.5 rounded-xl border border-cane-200 bg-cane-50/70 px-3.5 py-3 text-sm dark:border-cane-900/60 dark:bg-cane-950/40">
      <Leaf className="mt-0.5 size-4 shrink-0 text-cane-600 dark:text-cane-400" />
      <p className="text-slate-700 dark:text-slate-300">
        {kind === 'plant' ? (
          <>
            <span className="font-semibold">Upload a sugarcane photo only.</span> Photos of other
            crops, soil on its own, or unrelated subjects are rejected automatically — the analysis
            only runs once sugarcane is detected.
          </>
        ) : (
          <>
            <span className="font-semibold">Upload a soil photo only.</span> Fill the frame with the
            bare soil surface of your field, in daylight. Plants, people and unrelated subjects are
            rejected automatically — no analysis runs until soil is confirmed.
          </>
        )}
      </p>
    </div>
  )
}

/** Shown while the gate is running, immediately after a file is chosen. */
export function CheckingNotice({ kind }: { kind: 'plant' | 'soil' }) {
  return (
    <div className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
      <Search className="size-4 shrink-0 animate-pulse text-slate-500" />
      <span className="font-medium text-slate-700 dark:text-slate-300">
        🔍 {kind === 'plant' ? 'Checking for sugarcane…' : 'Checking image…'} Please wait.
      </span>
    </div>
  )
}

/**
 * Outcome of the image gate.
 *
 * A rejection is not an error - it is the system declining to invent an answer
 * for an image it cannot analyse, so it reads as guidance rather than failure.
 * `unclear` outcomes are separated from outright rejections because they are
 * fixed by retaking the photo, not by photographing something else.
 */
export function ValidationNotice({
  validation,
  onRetry,
}: {
  validation: ImageValidation
  onRetry?: () => void
}) {
  const { isSugarcane, imageType, title, message, confidence, checked_by, notes, scores } =
    validation

  if (isSugarcane && imageType === 'plant_unverified') {
    return (
      <div className="rounded-xl border border-amber-300 bg-amber-50 px-3.5 py-3 dark:border-amber-800/60 dark:bg-amber-950/30">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <div className="text-sm">
            <p className="font-semibold text-amber-900 dark:text-amber-200">⚠️ {title}</p>
            <p className="mt-1 text-amber-800 dark:text-amber-300">{message}</p>
          </div>
        </div>
      </div>
    )
  }

  if (isSugarcane) {
    return (
      <div className="flex items-center gap-2.5 rounded-xl border border-cane-300 bg-cane-50 px-3.5 py-3 text-sm dark:border-cane-800/60 dark:bg-cane-950/40">
        <CheckCircle2 className="size-4 shrink-0 text-cane-600 dark:text-cane-400" />
        <span className="font-medium text-cane-900 dark:text-cane-200">
          ✅ {message}
          <span className="ml-1 font-normal opacity-70">
            ({Math.round(confidence * 100)}% confidence)
          </span>
        </span>
      </div>
    )
  }

  const unclear = imageType === 'unclear_soil' || imageType === 'unclear'
  const bestOther = scores ? Object.entries(scores).sort((a, b) => b[1] - a[1])[0] : null

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3.5 dark:border-amber-800/60 dark:bg-amber-950/30">
      <div className="flex items-start gap-2.5">
        <XCircle className="mt-0.5 size-4 shrink-0 text-amber-600 dark:text-amber-400" />
        <div className="min-w-0 flex-1 text-sm">
          <p className="font-semibold text-amber-900 dark:text-amber-200">⚠️ {title}</p>
          <p className="mt-1 leading-relaxed text-amber-800 dark:text-amber-300">{message}</p>

          <p className="mt-2 text-xs font-medium text-amber-700/90 dark:text-amber-400/80">
            {unclear
              ? 'No analysis was run — nothing is estimated from a photo this unclear.'
              : 'No analysis was run, so no soil type, nutrients, variety or fertilizer advice was produced from this image.'}
          </p>

          {notes?.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs text-amber-700/90 dark:text-amber-400/80">
              {notes.map((note) => (
                <li key={note} className="flex gap-1.5">
                  <Info className="mt-0.5 size-3 shrink-0" />
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          )}

          <p className="mt-2 text-xs text-amber-700/70 dark:text-amber-400/60">
            Checked by{' '}
            {checked_by === 'trained_model'
              ? 'the trained sugarcane validator'
              : 'image colour analysis'}
            {bestOther ? ` · best match "${bestOther[0]}" at ${Math.round(bestOther[1] * 100)}%` : ''}
          </p>

          {onRetry && (
            <button type="button" onClick={onRetry} className="btn-secondary mt-3 !py-1.5 text-xs">
              Choose another photo
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
