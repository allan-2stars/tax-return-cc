'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { recover } from '@/lib/api/auth'

interface RecoverForm {
  recoveryKey: string
  newPassword: string
}

export default function RecoverPage() {
  const router = useRouter()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { isSubmitting, errors },
  } = useForm<RecoverForm>({ mode: 'onTouched' })

  async function onSubmit({ recoveryKey, newPassword }: RecoverForm) {
    setServerError(null)
    try {
      await recover(recoveryKey, newPassword)
      router.replace('/login')
    } catch (err: unknown) {
      console.error(err)
      if (axios.isAxiosError(err)) {
        const message = err.response?.data?.detail?.message
        setServerError(message ?? 'Recovery failed. Please check your key and try again.')
      } else {
        setServerError('Connection error. Please check your network and try again.')
      }
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="font-display text-3xl font-semibold text-text-primary mb-2">
          Recover workspace
        </h1>
        <p className="font-ui text-sm text-text-muted mb-8">
          Enter your recovery key to set a new password.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label
              htmlFor="recoveryKey"
              className="block font-ui text-sm font-medium text-text-body mb-1"
            >
              Recovery key
            </label>
            <input
              id="recoveryKey"
              type="text"
              autoFocus
              autoComplete="off"
              className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
              {...register('recoveryKey', { required: 'Recovery key is required' })}
            />
            {errors.recoveryKey && (
              <p role="alert" className="font-ui text-sm text-risk-high mt-1">
                {errors.recoveryKey.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="newPassword"
              className="block font-ui text-sm font-medium text-text-body mb-1"
            >
              New password
            </label>
            <input
              id="newPassword"
              type="password"
              autoComplete="new-password"
              className="w-full px-4 py-3 rounded-md border border-border bg-surface font-ui text-base text-text-primary focus:outline-none focus:shadow-focus"
              {...register('newPassword', { required: 'New password is required' })}
            />
            {errors.newPassword && (
              <p role="alert" className="font-ui text-sm text-risk-high mt-1">
                {errors.newPassword.message}
              </p>
            )}
          </div>

          {serverError && (
            <p role="alert" className="font-ui text-sm text-risk-high">
              {serverError}
            </p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 rounded-md bg-accent hover:bg-accent-hover text-white font-ui font-medium text-base disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? 'Resetting…' : 'Reset password'}
          </button>
        </form>
      </div>
    </div>
  )
}

