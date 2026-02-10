package com.voxdocs.agent.intent

import android.util.Log
import com.voxdocs.agent.api.VoiceIntent
import com.voxdocs.agent.api.VoiceIntentType

/**
 * Rule-based intent classifier.
 *
 * Parses the SpeechRecognizer transcript to determine:
 *  1. Intent type (CREATE_TASK_OR_NOTE vs READ_OPEN_TASKS)
 *  2. Case name (explicit mention, e.g. "für Demian" or "for Demian")
 *
 * Supports both German and English trigger phrases.
 */
object IntentParser {

    private const val TAG = "IntentParser"

    // ── READ_OPEN_TASKS patterns ────────────────────────────────────

    private val READ_PATTERNS = listOf(
        // German
        Regex("(?:offene?|ausstehende?)\\s+(?:aufgaben?|tasks?)", RegexOption.IGNORE_CASE),
        Regex("(?:zeig|sag|lies|nenn).*(?:aufgaben?|tasks?|to.?do)", RegexOption.IGNORE_CASE),
        Regex("was\\s+(?:muss|mussen|müssen|steht)\\s+(?:noch|an)", RegexOption.IGNORE_CASE),
        Regex("was\\s+gibt\\s+es.*zu\\s+tun", RegexOption.IGNORE_CASE),
        // English
        Regex("(?:open|pending)\\s+tasks?", RegexOption.IGNORE_CASE),
        Regex("(?:tell|read|show|list).*tasks?", RegexOption.IGNORE_CASE),
        Regex("what.*(?:to\\s+do|tasks?|open)", RegexOption.IGNORE_CASE),
    )

    // ── Case-name extraction patterns (ordered by specificity) ──────

    private val CASE_PATTERNS = listOf(
        // "für Demian, ..." or "for Demian, ..."
        Regex("(?:für|fur|for)\\s+([A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß]+)", RegexOption.IGNORE_CASE),
        // "Fall Demian" / "case Demian"
        Regex("(?:fall|case|akte)\\s+([A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß]+)", RegexOption.IGNORE_CASE),
        // "bei Demian"
        Regex("bei\\s+([A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß]+)", RegexOption.IGNORE_CASE),
        // "Demian:" at start of sentence
        Regex("^([A-ZÄÖÜa-zäöüß][A-ZÄÖÜa-zäöüß]+):", RegexOption.IGNORE_CASE),
    )

    // ── Words to exclude from case name match (common false positives) ──

    private val EXCLUDED_NAMES = setOf(
        "voxdocs", "vox", "docs", "hey", "hallo", "mir", "mich", "die",
        "der", "das", "den", "dem", "ein", "eine", "einen", "meine",
        "the", "me", "my", "all", "offene", "aufgaben", "tasks",
    )

    // ── Public API ──────────────────────────────────────────────────

    /**
     * Parse a raw transcript into a [VoiceIntent].
     *
     * @param text  The raw text from SpeechRecognizer
     * @return Parsed intent with type and optional case name
     */
    fun parse(text: String): VoiceIntent {
        // Strip wakeword prefix if present
        val cleaned = text
            .replace(Regex("^(hey\\s+)?vox\\s*docs\\s*[,.]?\\s*", RegexOption.IGNORE_CASE), "")
            .trim()

        Log.d(TAG, "Parsing: \"$cleaned\" (raw: \"$text\")")

        // 1. Detect intent type
        val isRead = READ_PATTERNS.any { it.containsMatchIn(cleaned) }
        val intentType = if (isRead) VoiceIntentType.READ_OPEN_TASKS else VoiceIntentType.CREATE_TASK_OR_NOTE

        // 2. Extract case name
        var caseName: String? = null
        for (pattern in CASE_PATTERNS) {
            val match = pattern.find(cleaned)
            if (match != null) {
                val candidate = match.groupValues[1].trim()
                if (candidate.lowercase() !in EXCLUDED_NAMES && candidate.length >= 2) {
                    caseName = candidate
                    break
                }
            }
        }

        Log.i(TAG, "Intent: $intentType, case: $caseName")
        return VoiceIntent(
            type = intentType,
            caseName = caseName,
            rawText = cleaned,
        )
    }
}
