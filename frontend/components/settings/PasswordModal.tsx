'use client'
import { useForm } from 'react-hook-form'

interface Props {
  title: string
  description?: string
  confirmLabel?: string
  emptyMessage?: string
  pending?: boolean
  error?: string | null
  onConfirm: (password: string) => void
  onCancel: () => void
}

export default function PasswordModal({
  title,
  description,
  confirmLabel = 'Confirm',
  emptyMessage = 'Password is required',
  pending,
  error,
  onConfirm,
  onCancel,
}: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<{ password: string }>()

  function onSubmit({ password }: { password: string }) {
    onConfirm(password)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-sm mx-4 bg-surface rounded-xl border border-border p-6 space-y-4">
        <h2 className="font-display text-lg font-semibold text-text-primary">{title}</h2>
        {description && (
          <p className="text-sm font-ui text-text-muted">{description}</p>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label
              htmlFor="modal-password"
              className="text-sm font-ui text-text-body block mb-1"
            >
              Password
            </label>
            <input
              id="modal-password"
              type="password"
              autoComplete="current-password"
              className="w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm font-ui"
              aria-label="Password"
              autoFocus
              {...register('password', { required: emptyMessage })}
            />
            {errors.password && (
              <p className="text-sm font-ui text-risk-high mt-1">
                {errors.password.message}
              </p>
            )}
          </div>
          {error && <p className="text-sm font-ui text-risk-high">{error}</p>}
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={pending}
              className="min-h-11 px-5 rounded-md bg-accent text-white text-sm font-ui font-semibold disabled:opacity-50"
            >
              {pending ? 'Working…' : confirmLabel}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="min-h-11 px-4 text-sm font-ui text-text-muted"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
