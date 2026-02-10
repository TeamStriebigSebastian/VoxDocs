package com.voxdocs.agent.intent

import com.voxdocs.agent.api.CaseInfo
import com.voxdocs.agent.api.CaseMatchResult
import kotlin.math.min

/**
 * Fuzzy matcher for spoken case names against the local case cache.
 *
 * Strategy:
 *  1. Exact match (case-insensitive)
 *  2. Levenshtein distance with threshold
 *  3. Contains / prefix match as fallback
 *  4. If multiple candidates are close → ambiguous
 */
object CaseMatcher {

    private const val MAX_EDIT_DISTANCE = 3
    private const val AMBIGUITY_MARGIN = 1  // if two candidates are within this margin → ambiguous

    /**
     * Find the best matching case for [spokenName].
     */
    fun match(spokenName: String, cases: List<CaseInfo>): CaseMatchResult {
        if (cases.isEmpty()) return CaseMatchResult.NoMatch

        val query = spokenName.lowercase().trim()

        // 1. Exact match
        val exact = cases.find { it.name.lowercase() == query }
        if (exact != null) return CaseMatchResult.Exact(exact)

        // 2. Levenshtein distance
        data class Scored(val case: CaseInfo, val distance: Int)

        val scored = cases
            .map { Scored(it, levenshtein(query, it.name.lowercase())) }
            .filter { it.distance <= MAX_EDIT_DISTANCE }
            .sortedBy { it.distance }

        if (scored.isNotEmpty()) {
            val best = scored.first()
            // Check for ambiguity: multiple candidates within margin
            val close = scored.filter { it.distance <= best.distance + AMBIGUITY_MARGIN }
            if (close.size > 1) {
                return CaseMatchResult.Ambiguous(close.map { it.case })
            }
            return CaseMatchResult.Fuzzy(best.case, best.distance)
        }

        // 3. Contains / starts-with fallback
        val containing = cases.filter { it.name.lowercase().contains(query) || query.contains(it.name.lowercase()) }
        if (containing.size == 1) {
            return CaseMatchResult.Fuzzy(containing.first(), MAX_EDIT_DISTANCE)
        }
        if (containing.size > 1) {
            return CaseMatchResult.Ambiguous(containing)
        }

        return CaseMatchResult.NoMatch
    }

    // ── Levenshtein distance ────────────────────────────────────────

    fun levenshtein(a: String, b: String): Int {
        val m = a.length
        val n = b.length
        val dp = Array(m + 1) { IntArray(n + 1) }

        for (i in 0..m) dp[i][0] = i
        for (j in 0..n) dp[0][j] = j

        for (i in 1..m) {
            for (j in 1..n) {
                val cost = if (a[i - 1] == b[j - 1]) 0 else 1
                dp[i][j] = min(min(dp[i - 1][j] + 1, dp[i][j - 1] + 1), dp[i - 1][j - 1] + cost)
            }
        }
        return dp[m][n]
    }
}
