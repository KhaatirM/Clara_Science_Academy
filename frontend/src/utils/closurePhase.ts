export function phaseStepClass(isDone: boolean, isCurrent: boolean): string {
  const classes = ['mgmt-syc-phase-step']
  if (isDone) classes.push('is-done')
  if (isCurrent) classes.push('is-current')
  return classes.join(' ')
}

export function scheduledPhaseState(phase: string) {
  return {
    isDone: phase !== 'scheduled',
    isCurrent: phase === 'scheduled',
  }
}

export function studentWindowPhaseState(phase: string) {
  return {
    isDone: ['teacher_window', 'admin_window', 'finalized'].includes(phase),
    isCurrent: phase === 'student_window',
  }
}

export function teacherWindowPhaseState(phase: string) {
  return {
    isDone: ['admin_window', 'finalized'].includes(phase),
    isCurrent: phase === 'teacher_window',
  }
}

export function adminWindowPhaseState(phase: string) {
  return {
    isDone: phase === 'finalized',
    isCurrent: phase === 'admin_window',
  }
}

export function finalizedPhaseState(phase: string) {
  return {
    isDone: phase === 'finalized',
    isCurrent: phase === 'finalized',
  }
}
