/** Middle school starts at grade 6; elementary is K–5 (0–5). */
export function classSupportsSyllabus(gradeLevels?: number[] | null): boolean {
  return Array.isArray(gradeLevels) && gradeLevels.some((g) => Number(g) >= 6)
}
