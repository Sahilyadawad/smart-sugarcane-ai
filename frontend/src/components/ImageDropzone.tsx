import { useCallback, useEffect, useRef, useState } from 'react'
import { Camera, ImageUp, RefreshCw, X } from 'lucide-react'

const ACCEPTED = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/bmp', 'image/tiff']
const MAX_MB = 10

interface Props {
  onSelect: (file: File | null) => void
  disabled?: boolean
  hint?: string
  label?: string
}

export function ImageDropzone({ onSelect, disabled = false, hint, label = 'Upload a photo' }: Props) {
  const [preview, setPreview] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string>('')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Object URLs leak if they are not revoked when the preview changes.
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const accept = useCallback(
    (file: File | undefined) => {
      if (!file) return
      if (!ACCEPTED.includes(file.type.toLowerCase())) {
        setError(`"${file.name}" is not a supported image. Use JPG, PNG or WEBP.`)
        return
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        setError(`That image is ${(file.size / 1024 / 1024).toFixed(1)} MB. The limit is ${MAX_MB} MB.`)
        return
      }
      setError(null)
      setPreview((current) => {
        if (current) URL.revokeObjectURL(current)
        return URL.createObjectURL(file)
      })
      setFileName(file.name)
      onSelect(file)
    },
    [onSelect],
  )

  const clear = useCallback(() => {
    setPreview((current) => {
      if (current) URL.revokeObjectURL(current)
      return null
    })
    setFileName('')
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
    onSelect(null)
  }, [onSelect])

  if (preview) {
    return (
      <div className="space-y-3">
        <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 dark:border-slate-700 dark:bg-slate-800">
          <img src={preview} alt="Selected upload preview" className="max-h-80 w-full object-contain" />
          <button
            type="button"
            onClick={clear}
            disabled={disabled}
            className="absolute right-3 top-3 grid size-9 place-items-center rounded-full bg-slate-900/70 text-white backdrop-blur transition hover:bg-slate-900 disabled:opacity-50"
            aria-label="Remove selected image"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="flex items-center justify-between gap-3 text-sm">
          <span className="truncate text-slate-600 dark:text-slate-400">{fileName}</span>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
            className="btn-ghost shrink-0 px-3 py-1.5 text-xs"
          >
            <RefreshCw className="size-3.5" />
            Change
          </button>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={(event) => accept(event.target.files?.[0])}
        />
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            if (!disabled) inputRef.current?.click()
          }
        }}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          if (!disabled) accept(event.dataTransfer.files?.[0])
        }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-12 text-center transition ${
          dragging
            ? 'border-cane-500 bg-cane-50 dark:bg-cane-950/40'
            : 'border-slate-300 bg-slate-50 hover:border-cane-400 hover:bg-cane-50/50 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:bg-slate-800'
        } ${disabled ? 'pointer-events-none opacity-60' : ''}`}
      >
        <span className="grid size-14 place-items-center rounded-2xl bg-white text-cane-600 shadow-sm dark:bg-slate-900">
          {dragging ? <ImageUp className="size-7" /> : <Camera className="size-7" />}
        </span>
        <div>
          <p className="font-display text-base font-bold text-slate-800 dark:text-slate-100">
            {dragging ? 'Drop the photo here' : label}
          </p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Drag and drop, or click to browse
          </p>
          <p className="mt-2 text-xs text-slate-400">JPG, PNG or WEBP, up to {MAX_MB} MB</p>
        </div>
        {hint && (
          <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-500 dark:text-slate-400">{hint}</p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="hidden"
          onChange={(event) => accept(event.target.files?.[0])}
        />
      </div>
      {error && <p className="text-sm font-medium text-red-600 dark:text-red-400">{error}</p>}
    </div>
  )
}
