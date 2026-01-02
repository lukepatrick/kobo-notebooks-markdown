# Note-Taking Patterns for Better Wikilinks

When writing notes on your Kobo Sage, these patterns help the AI (and basic heuristics) identify content that should become wikilinks in Obsidian.

---

## Patterns That Work Well

### 1. Wikilinks You Write Manually

If you write `[[Note Title]]` in your handwriting, the text recognition preserves it:

```
Reading [[A Calendar of Wisdom]] by [[Leo Tolstoy]] today.
```

**Tip:** Use this for links you're certain about.

### 2. Proper Capitalization for Names

The AI recognizes proper nouns when capitalized correctly:

```
Met with John Smith to discuss the project.
Finished reading The Great Gatsby.
Visited the Museum of Modern Art.
```

These become: `[[John Smith]]`, `[[The Great Gatsby]]`, `[[Museum of Modern Art]]`

### 3. Quotation Marks for Titles

Quoted phrases are strong candidates for links:

```
Started "Deep Work" by Cal Newport.
The concept of "flow state" is fascinating.
```

These become: `[[Deep Work]]`, `[[flow state]]`

### 4. "By" Attribution Pattern

Author names after "by" are automatically detected:

```
Quote from Meditations by Marcus Aurelius
Podcast by Tim Ferriss on productivity
```

These become: `[[Marcus Aurelius]]`, `[[Tim Ferriss]]`

---

## Delimiter Patterns for Structure

### Use Colons for Categories

```
Book: The Pragmatic Programmer
Person: Ada Lovelace
Concept: Spaced Repetition
Location: San Francisco
```

The AI can split these and create appropriate tags or links.

### Use Arrows for Relationships

```
Stoicism -> Marcus Aurelius -> Meditations
Python -> FastAPI -> Async Programming
```

Helps the AI understand knowledge graph relationships.

### Hashtags for Tags

Write hashtags and they'll be converted to Obsidian tags:

```
#productivity #reading #2026
```

---

## Templates for Common Note Types

### Book Notes Template

```
BOOK: [Title]
AUTHOR: [Author Name]
DATE: [When you read it]

Key Ideas:
- [Idea 1]
- [Idea 2]

Quotes:
"[Quote text]" - p.[page]

Related: [Other books/concepts]
```

### Meeting Notes Template

```
MEETING: [Topic]
DATE: [Date]
WITH: [Person 1], [Person 2]

Discussed:
- [Topic 1]
- [Topic 2]

Action Items:
- [ ] [Task 1]
- [ ] [Task 2]

Follow-up: [Next steps]
```

### Daily Journal Template

```
DATE: [YYYY-MM-DD]

Morning:
- [Activity/thought]

Afternoon:
- [Activity/thought]

Evening:
- [Activity/thought]

Grateful for: [Something]
Learned: [Something new]
```

### Idea Capture Template

```
IDEA: [Short title]

The Concept:
[Description]

Why It Matters:
[Importance]

Related To: [Existing notes/concepts]
Next Steps: [What to do with this]
```

---

## Special Markers for AI Processing

### Mark Entities Explicitly

Use angle brackets or parentheses with type markers:

```
(person: Albert Einstein) developed the theory of relativity
(book: "Thinking, Fast and Slow") by (person: Daniel Kahneman)
(concept: Second Brain) helps with knowledge management
```

### Mark Importance

Use asterisks or exclamation marks for emphasis:

```
*KEY INSIGHT* - The most important point
!REMEMBER! - Something to review later
?QUESTION? - Something to research
```

### Link Hints

When you want a specific link but don't want to write full wikilink syntax:

```
-> Links to Project Phoenix
<- From "Getting Things Done" methodology
~ Related to Zettelkasten
```

---

## Patterns to Avoid

### All Caps (Except Headers)

The AI may not recognize names in all caps:
- Bad: `JOHN SMITH said...`
- Good: `John Smith said...`

### Abbreviations Without Context

- Bad: `MTG w/ JS re: proj`
- Good: `Meeting with John Smith regarding the project`

### Run-on Sentences

Break up long thoughts for better parsing:
- Bad: `Talked to Bob who mentioned the Smith project which connects to the Johnson account...`
- Good: `Talked to Bob. He mentioned the Smith project. It connects to the Johnson account.`

---

## Configuration in kobo-md

The AI wikilink suggestions can be tuned via environment variables:

```bash
# Enable/disable AI processing
export KOBO_MD_AI_ENABLED=true

# Choose AI provider
export KOBO_MD_AI_PROVIDER=anthropic

# Enable wikilink suggestions
export KOBO_MD_SUGGEST_WIKILINKS=true

# Enable text cleanup
export KOBO_MD_CLEANUP_TEXT=true
```

Or create a `.env` file in your project:

```ini
KOBO_MD_AI_ENABLED=true
KOBO_MD_AI_PROVIDER=anthropic
KOBO_MD_SUGGEST_WIKILINKS=true
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Future AI Enhancements

The AI processor (Phase 2) will:

1. **Identify Proper Nouns** - Names, places, organizations, titles
2. **Suggest Existing Links** - Match against notes already in your vault
3. **Clean Up Recognition Errors** - Fix common handwriting misrecognitions
4. **Extract Structure** - Turn free-form notes into structured markdown
5. **Tag Suggestions** - Propose relevant tags based on content
6. **Date Normalization** - Convert various date formats to ISO format

---

*These patterns are designed to work with Kobo's text recognition and the kobo-md AI processing pipeline.*
