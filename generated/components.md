# OpenUI component catalog

Generated from the exact libraries shipped in this release. UI uses `Stack` as root; email uses `EmailTemplate`. Arguments are positional. Gateway is optional.

## Interactive UI (103)

### Card

```text
Card(children: (TextContent | MarkDownRenderer | CardHeader | Callout | TextCallout | CodeBlock | Image | ImageBlock | ImageGallery | Separator | HorizontalBarChart | RadarChart | PieChart | RadialChart | SingleStackedBarChart | ScatterChart | AreaChart | BarChart | LineChart | Table | TagBlock | Form | Buttons | IconButton | Steps | InlineHeader | EntityList | EditableTable | SnippetCardBlock | OverviewCardBlock | ContextCardBlock | CompositeCardBlock | VisualCardBlock | Tabs | Carousel | Stack | ChartJS | ImageCard | ImageCarousel | ImageGrid | SourceLink | Dashboard | DashboardSection | MetricCard | ProgressMeter | KeyValueList | Timeline | KanbanBoard | ComparisonTable | Agenda | FileList | StatusBadge | EmptyState | QuoteBlock | Checklist | Rating | ComponentTemplate)[], variant?: "card" | "sunk" | "clear", direction?: "row" | "column", gap?: "none" | "xs" | "s" | "m" | "l" | "xl" | "2xl", align?: "start" | "center" | "end" | "stretch" | "baseline", justify?: "start" | "center" | "end" | "between" | "around" | "evenly", wrap?: boolean)
```
Styled container. variant: "card" (default, elevated) | "sunk" (recessed) | "clear" (transparent). Always full width. Accepts all Stack flex params (default: direction "column"). Cards flex to share space in row/wrap layouts.

### CardHeader

```text
CardHeader(title?: string, subtitle?: string)
```
Header with optional title and subtitle

### TextContent

```text
TextContent(text: string, size?: "small" | "default" | "large" | "small-heavy" | "large-heavy")
```
Text block. Supports markdown. Optional size: "small" | "default" | "large" | "small-heavy" | "large-heavy".

### MarkDownRenderer

```text
MarkDownRenderer(textMarkdown: string, variant?: "clear" | "card" | "sunk")
```
Renders markdown text with optional container variant

### Callout

```text
Callout(variant: "info" | "warning" | "error" | "success" | "neutral", title: string, description: string, visible?: $binding<boolean>)
```
Callout banner. Optional visible is a reactive $boolean — auto-dismisses after 3s by setting $visible to false.

### TextCallout

```text
TextCallout(variant?: "neutral" | "info" | "warning" | "success" | "danger", title?: string, description?: string)
```
Text callout with variant, title, and description

### Image

```text
Image(alt: string, src?: string)
```
Image with alt text and optional URL

### ImageBlock

```text
ImageBlock(src: string, alt?: string)
```
Image block with loading state

### ImageGallery

```text
ImageGallery(images: {src: string, alt?: string, details?: string}[])
```
Gallery grid of images with modal preview

### CodeBlock

```text
CodeBlock(language: string, codeString: string)
```
Syntax-highlighted code block

### InlineHeader

```text
InlineHeader(heading: string, description?: string)
```
Compact section heading with an optional one-line description, for use inside cards.

### Table

```text
Table(columns: Col[])
```
Data table — column-oriented. Each Col holds its own data array.

### Col

```text
Col(label: string, data: any, type?: "string" | "number" | "action")
```
Column definition — holds label + data array

### EditableTable

```text
EditableTable(name?: string, columns?: {type: "text" | "number" | "date-single" | "select" | "url", key?: string, header?: string, width?: number, options?: {value: string, label: string}[]}[], data?: {id: string, values: (string | number)[]}[])
```
Spreadsheet-like table whose cells the user can edit inline (text, number, url, date, select columns); edits are saved back as a form field

### BarChart

```text
BarChart(labels: string[], series: Series[], variant?: "grouped" | "stacked", xLabel?: string, yLabel?: string, height?: number)
```
Vertical bars; use for comparing values across categories with one or more series

### LineChart

```text
LineChart(labels: string[], series: Series[], variant?: "linear" | "natural" | "step", xLabel?: string, yLabel?: string, height?: number)
```
Lines over categories; use for trends and continuous data over time

### AreaChart

```text
AreaChart(labels: string[], series: Series[], variant?: "linear" | "natural" | "step", xLabel?: string, yLabel?: string, height?: number)
```
Filled area under lines; use for cumulative totals or volume trends over time

### RadarChart

```text
RadarChart(labels: string[], series: Series[])
```
Spider/web chart; use for comparing multiple variables across one or more entities

### HorizontalBarChart

```text
HorizontalBarChart(labels: string[], series: Series[], variant?: "grouped" | "stacked", xLabel?: string, yLabel?: string)
```
Horizontal bars; prefer when category labels are long or for ranked lists

### Series

```text
Series(category: string, values: number[])
```
One data series

### PieChart

```text
PieChart(labels: string[], values: number[], variant?: "pie" | "donut", appearance?: "circular" | "semiCircular")
```
Circular slices; use plucked arrays: PieChart(data.categories, data.values)

### RadialChart

```text
RadialChart(labels: string[], values: number[])
```
Radial bars; use plucked arrays: RadialChart(data.categories, data.values)

### SingleStackedBarChart

```text
SingleStackedBarChart(labels: string[], values: number[])
```
Single horizontal stacked bar; use plucked arrays: SingleStackedBarChart(data.categories, data.values)

### Slice

```text
Slice(category: string, value: number)
```
One slice with label and numeric value

### ScatterChart

```text
ScatterChart(datasets: ScatterSeries[], xLabel?: string, yLabel?: string)
```
X/Y scatter plot; use for correlations, distributions, and clustering

### ScatterSeries

```text
ScatterSeries(name: string, points: Point[])
```
Named dataset

### Point

```text
Point(x: number, y: number, z?: number)
```
Data point with numeric coordinates

### Form

```text
Form(name: string, buttons: Buttons, fields?: FormControl[])
```
Form container with fields and explicit action buttons

### FormControl

```text
FormControl(label: string, input: Input | TextArea | Select | DatePicker | Slider | CheckBoxGroup | RadioGroup | Chips | OptionCards, hint?: string)
```
Field with label, input component, and optional hint text

### Label

```text
Label(text: string)
```
Text label

### Input

```text
Input(name: string, placeholder?: string, type?: "text" | "email" | "number" | "url", rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<string>)
```


### TextArea

```text
TextArea(name: string, placeholder?: string, rows?: number, rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<string>)
```


### Select

```text
Select(name: string, items: SelectItem[], placeholder?: string, rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<string>, size?: "small" | "medium" | "large")
```


### SelectItem

```text
SelectItem(value: string, label: string)
```
Option for Select

### DatePicker

```text
DatePicker(name: string, mode?: "single" | "range", rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<any>)
```


### Slider

```text
Slider(name: string, variant: "continuous" | "discrete", min: number, max: number, step?: number, defaultValue?: number[], label?: string, rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<number[]>)
```
Numeric slider input; supports continuous and discrete (stepped) variants

### CheckBoxGroup

```text
CheckBoxGroup(name: string, items: CheckBoxItem[], rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<Record<string, boolean>>)
```


### CheckBoxItem

```text
CheckBoxItem(label: string, description: string, name: string, defaultChecked?: boolean)
```


### RadioGroup

```text
RadioGroup(name: string, items: RadioItem[], defaultValue?: string, rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, value?: $binding<string>)
```


### RadioItem

```text
RadioItem(label: string, description: string, value: string)
```


### SwitchGroup

```text
SwitchGroup(name: string, items: SwitchItem[], variant?: "clear" | "card" | "sunk", value?: $binding<Record<string, boolean>>)
```
Group of switch toggles

### SwitchItem

```text
SwitchItem(label?: string, description?: string, name: string, defaultChecked?: boolean)
```
Individual switch toggle

### ChipItem

```text
ChipItem(value: string, label: string, icon?: Icon, disabled?: boolean)
```
A single selectable chip inside a Chips group, with a value, label and optional icon.

### Chips

```text
Chips(name: string, type?: "single" | "multiple", items?: ChipItem[], rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, defaultValue?: string | string[])
```
A form field of compact selectable chips for choosing one or many short options; the selection is stored under `name`.

### OptionCard

```text
OptionCard(value: string, title: string, subtitle?: string, topContent?: Icon | Image, disabled?: boolean)
```
A single selectable card inside an OptionCards group, with a value, title, optional subtitle and an optional Icon or Image on top.

### OptionCards

```text
OptionCards(name: string, type?: "single" | "multiple", items?: OptionCard[], rules?: {required?: boolean, email?: boolean, numeric?: boolean, min?: number, max?: number, minLength?: number, maxLength?: number}, defaultValue?: string | string[])
```
A form field of selectable cards (title, optional subtitle, optional icon or image) laid out in a responsive grid for choosing one or many options; the selection is stored under `name`.

### Button

```text
Button(label: string, action?: ActionExpression, variant?: "primary" | "secondary" | "tertiary", type?: "normal" | "destructive", size?: "extra-small" | "small" | "medium" | "large")
```
Clickable button

### Buttons

```text
Buttons(buttons: Button[], direction?: "row" | "column")
```
Group of Button components. direction: "row" (default) | "column".

### IconButton

```text
IconButton(name: string, icon: Icon, action?: ActionExpression, variant?: "primary" | "secondary" | "tertiary", size?: "extra-small" | "small" | "medium" | "large", shape?: "square" | "circle")
```
Icon-only button. name is the accessible label and the action label; icon is an Icon; action fires on click.

### Stack

```text
Stack(children: any[], direction?: "row" | "column", gap?: "none" | "xs" | "s" | "m" | "l" | "xl" | "2xl", align?: "start" | "center" | "end" | "stretch" | "baseline", justify?: "start" | "center" | "end" | "between" | "around" | "evenly", wrap?: boolean)
```
Flex container. direction: "row"|"column" (default "column"). gap: "none"|"xs"|"s"|"m"|"l"|"xl"|"2xl" (default "m"). align: "start"|"center"|"end"|"stretch"|"baseline". justify: "start"|"center"|"end"|"between"|"around"|"evenly".

### Tabs

```text
Tabs(items: TabItem[])
```
Tabbed container

### TabItem

```text
TabItem(value: string, trigger: string, content: (TextContent | MarkDownRenderer | CardHeader | Callout | TextCallout | CodeBlock | Image | ImageBlock | ImageGallery | Separator | HorizontalBarChart | RadarChart | PieChart | RadialChart | SingleStackedBarChart | ScatterChart | AreaChart | BarChart | LineChart | Table | TagBlock | Form | Buttons | IconButton | Steps | InlineHeader | EntityList | EditableTable | SnippetCardBlock | OverviewCardBlock | ContextCardBlock | CompositeCardBlock | VisualCardBlock | ChartJS | ImageCard | ImageCarousel | ImageGrid | SourceLink | Dashboard | DashboardSection | MetricCard | ProgressMeter | KeyValueList | Timeline | KanbanBoard | ComparisonTable | Agenda | FileList | StatusBadge | EmptyState | QuoteBlock | Checklist | Rating | ComponentTemplate)[])
```
value is unique id, trigger is tab label, content is array of components

### Accordion

```text
Accordion(items: AccordionItem[])
```
Collapsible sections

### AccordionItem

```text
AccordionItem(value: string, trigger: string, content: (TextContent | MarkDownRenderer | CardHeader | Callout | TextCallout | CodeBlock | Image | ImageBlock | ImageGallery | Separator | HorizontalBarChart | RadarChart | PieChart | RadialChart | SingleStackedBarChart | ScatterChart | AreaChart | BarChart | LineChart | Table | TagBlock | Form | Buttons | IconButton | Steps | InlineHeader | EntityList | EditableTable | SnippetCardBlock | OverviewCardBlock | ContextCardBlock | CompositeCardBlock | VisualCardBlock)[])
```
value is unique id, trigger is section title

### Steps

```text
Steps(items: StepsItem[])
```
Step-by-step guide

### StepsItem

```text
StepsItem(title: string, details: string)
```
title and details text for one step

### Carousel

```text
Carousel(children: (TextContent | MarkDownRenderer | CardHeader | Callout | TextCallout | CodeBlock | Image | ImageBlock | ImageGallery | Separator | HorizontalBarChart | RadarChart | PieChart | RadialChart | SingleStackedBarChart | ScatterChart | AreaChart | BarChart | LineChart | Table | TagBlock | Form | Buttons | IconButton | Steps | InlineHeader | EntityList | EditableTable | SnippetCardBlock | OverviewCardBlock | ContextCardBlock | CompositeCardBlock | VisualCardBlock | ChartJS | ImageCard | ImageCarousel | ImageGrid | SourceLink | Dashboard | DashboardSection | MetricCard | ProgressMeter | KeyValueList | Timeline | KanbanBoard | ComparisonTable | Agenda | FileList | StatusBadge | EmptyState | QuoteBlock | Checklist | Rating | ComponentTemplate)[][], variant?: "card" | "sunk")
```
Horizontal scrollable carousel

### Separator

```text
Separator(orientation?: "horizontal" | "vertical", decorative?: boolean)
```
Visual divider between content sections

### TagBlock

```text
TagBlock(tags: string[], size?: "sm" | "md" | "lg")
```
tags is an array of strings; optional size sm | md | lg

### Tag

```text
Tag(text: string, icon?: Icon, size?: "sm" | "md" | "lg", variant?: "neutral" | "info" | "success" | "warning" | "danger")
```
Styled tag/badge with optional Icon and variant

### Icon

```text
Icon(name: string, category?: string)
```
A lucide icon by kebab-case name (e.g. 'circle-check'). Optional category picks a topical fallback when the name doesn't resolve.

### EntityList

```text
EntityList(rows?: {left: string, right: string, rightVariant?: "text" | "number"}[], size?: "small" | "default", header?: {left: string, right: string, rightVariant?: "text" | "number"}, footer?: {left: string, right: string, rightVariant?: "text" | "number"})
```
Two-column key/value rows (left label, right value). size 'default' supports optional header and footer rows; rightVariant 'number' uses tabular numbers.

### ListBlock

```text
ListBlock(items: ListItem[], variant?: "number" | "image", size?: "default" | "small")
```
A list of items with number or image indicators. Each item can optionally have an action. size small renders a compact list.

### ListItem

```text
ListItem(title: string, subtitle?: string, image?: {src: string, alt: string}, actionLabel?: string, action?: ActionExpression)
```
Item in a ListBlock — displays a title with an optional subtitle and image. When action is provided, the item becomes clickable.

### Text

```text
Text(variant?: "text" | "number", value: string, subtext?: string, subtextVariant?: "text" | "number" | "metric", size?: "xs" | "sm" | "md" | "lg")
```
Plain text line with optional subtext. variant 'number' uses tabular number styling; subtextVariant 'metric' colors a leading +/- subtext green/red.

### BoldText

```text
BoldText(variant?: "text" | "number", value: string, subtext?: string, subtextVariant?: "text" | "number" | "metric", size?: "xs" | "sm" | "md" | "lg")
```
Emphasized (bold) text line with optional subtext. variant 'number' uses tabular number styling; subtextVariant 'metric' colors a leading +/- subtext green/red.

### IconText

```text
IconText(icon: Icon, iconVariant?: "neutral" | "info" | "success" | "warning" | "danger" | "inverted" | "filled" | "soft", iconSize?: "xs" | "s" | "m" | "l" | "xl" | "sm" | "md" | "lg", title: string, subtitle?: string, bold?: boolean, layout?: "horizontal" | "vertical")
```
An icon badge with a title and optional subtitle, laid out horizontally or vertically. iconVariant sets the badge color.

### ImageText

```text
ImageText(src: string, alt?: string, title: string, subtitle?: string, bold?: boolean, layout?: "horizontal" | "vertical", imageSize?: number)
```
A small square image (thumbnail/avatar) with a title and optional subtitle. src must be a real image URL.

### ImageTextLarge

```text
ImageTextLarge(src: string, alt?: string, title: string, subtitle?: string, bold?: boolean)
```
A full-width banner image above a bold title and optional subtitle. src must be a real image URL.

### MetricIndicatorInline

```text
MetricIndicatorInline(value: string, subtext?: string, trend?: {direction: "up" | "down", value: number})
```
Headline metric value with an optional +/- percentage trend and subtext, all on one line.

### MetricIndicatorWithStrikethrough

```text
MetricIndicatorWithStrikethrough(value: string, subtext?: string, previousValue?: string, trend?: {direction: "up" | "down", value: number})
```
Headline metric value with an optional struck-through previousValue, a +/- percentage trend, and subtext below.

### SnippetCardItem

```text
SnippetCardItem(id?: string, lhs: IconText | ImageText, rhs?: Text | BoldText)
```
One row-style snippet card: a label on the left (IconText or ImageText) and an optional value on the right (Text or BoldText).

### SnippetCardBlock

```text
SnippetCardBlock(items: SnippetCardItem[], layout?: "grid", responsive?: boolean, action?: ActionExpression, gap?: number | string)
```
A responsive grid of compact label/value cards (2 per row) for showing several short facts side by side; optionally clickable with a shared action.

### OverviewCardItem

```text
OverviewCardItem(id?: string, top: IconText | ImageText | Text, bottom?: MetricIndicatorInline)
```
One overview card: a heading slot at the top (IconText, ImageText or Text) and an optional MetricIndicatorInline at the bottom.

### OverviewCardBlock

```text
OverviewCardBlock(items: OverviewCardItem[], layout?: "grid" | "carousel", responsive?: boolean, action?: ActionExpression, gap?: number | string)
```
A grid or horizontal carousel of compact overview cards, each with a heading (icon/image/text) on top and an inline metric below; optionally clickable with a shared action.

### ContextCardItem

```text
ContextCardItem(id?: string, title: string | Tag, body?: string, bgColor?: "gray", bgImageSrc?: string, bgImageAlt?: string)
```
A single card inside a ContextCardBlock: a title (plain string or Tag), an optional markdown body, and an optional gray tint or background image.

### ContextCardBlock

```text
ContextCardBlock(items: ContextCardItem[], layout?: "grid" | "carousel", responsive?: boolean, action?: ActionExpression, gap?: number | string)
```
A grid or carousel of compact tinted context cards (title or tag plus a short bold body); an optional action makes every card clickable.

### CompositeCardItem

```text
CompositeCardItem(id?: string, header?: IconText | ImageText | ImageTextLarge | Text | Image, body?: (Text | BoldText | MetricIndicatorInline | IconText | Image | AreaChart | BarChart | LineChart | ListBlock | TagBlock | EntityList)[], footer?: {price?: BoldText | MetricIndicatorWithStrikethrough, button?: Button})
```
A single card inside a CompositeCardBlock: an optional header (icon/image/text), a stack of body elements (text, metrics, charts, lists, tags), and an optional price/button footer.

### CompositeCardBlock

```text
CompositeCardBlock(items: CompositeCardItem[], layout?: "grid" | "carousel", responsive?: boolean, action?: ActionExpression, gap?: number | string)
```
A two-per-row grid or carousel of rich cards, each with an optional header, stacked body content (text, metrics, charts, lists, tags) and a price/button footer; an optional action makes every card clickable.

### VisualCardItem

```text
VisualCardItem(body: BoldText, id?: string, bgImageSrc?: string, tag?: Tag, bgImageAlt?: string)
```
A single photo-first card inside a VisualCardBlock: a BoldText body panel, an optional Tag, and a background image (bgImageSrc must be a real URL; bgImageAlt is its alt text).

### VisualCardBlock

```text
VisualCardBlock(items: VisualCardItem[], layout?: "grid" | "carousel", responsive?: boolean, action?: ActionExpression, gap?: number | string)
```
A grid or carousel of photo-first cards: a full-bleed background image with a tag on top and a bold text panel at the bottom; an optional action makes every card clickable.

### Modal

```text
Modal(title: string, open?: $binding<boolean>, children: (TextContent | MarkDownRenderer | CardHeader | Callout | TextCallout | CodeBlock | Image | ImageBlock | ImageGallery | Separator | HorizontalBarChart | RadarChart | PieChart | RadialChart | SingleStackedBarChart | ScatterChart | AreaChart | BarChart | LineChart | Table | TagBlock | Form | Buttons | IconButton | Steps | InlineHeader | EntityList | EditableTable | SnippetCardBlock | OverviewCardBlock | ContextCardBlock | CompositeCardBlock | VisualCardBlock)[], size?: "sm" | "md" | "lg")
```
Modal dialog. open is a reactive $boolean binding — set to true to open, X/Escape/backdrop auto-closes. Put Form with buttons inside children.

### ChartJS

```text
ChartJS(title: string, type: "bar" | "line" | "area" | "pie" | "doughnut" | "radar" | "polarArea" | "scatter" | "bubble", labels: string[], datasets: {label: string, data: (number | {x: number, y: number, r?: number} | any)[], type?: "bar" | "line"}[], stacked?: boolean, horizontal?: boolean, description?: string)
```
Chart.js canvas chart with accessible data table. Types: bar, line, area, pie, doughnut, radar, polarArea, scatter, bubble. datasets are objects {label,data,type?}; scatter/bubble data are {x,y,r?}. Per-series bar/line type makes mixed charts. Maximum 12 series and 500 points each. No executable options.

### ImageCard

```text
ImageCard(title: string, imageUrl: string, alt: string, description?: string, sourceUrl?: string, sourceName?: string, badge?: string)
```
Image search result or recommendation with image, alt text, description, source-page link and optional badge. Use actual HTTPS URLs returned by search or supplied by the user; never invent URLs or provenance. Broken/CORS-blocked images have an accessible fallback.

### ImageCarousel

```text
ImageCarousel(title: string, items: {title: string, imageUrl: string, alt: string, description?: string, sourceUrl?: string, sourceName?: string, badge?: string}[])
```
Responsive, keyboard-operable horizontal image cards. items are objects in ImageCard prop shape; maximum 24. No auto-play. Include sourceUrl/sourceName for search provenance.

### ImageGrid

```text
ImageGrid(title: string, items: {title: string, imageUrl: string, alt: string, description?: string, sourceUrl?: string, sourceName?: string, badge?: string}[])
```
Responsive grid of up to 24 image search results or recommendations. items are objects with title,imageUrl,alt,description?,sourceUrl?,sourceName?,badge?.

### SourceLink

```text
SourceLink(label: string, url: string, note?: string)
```
Named source/citation link for facts or image attribution. HTTPS only.

### Dashboard

```text
Dashboard(title: string, description: string, children: any[], columns?: "one" | "two" | "three")
```
Responsive dashboard grid with a title and description. Children are panels, metrics, charts, forms or image collections. Columns collapse on narrow screens.

### DashboardSection

```text
DashboardSection(title: string, children: any[], description?: string)
```
Named panel for grouping a dashboard chart, form or related content.

### MetricCard

```text
MetricCard(label: string, value: string, detail?: string, trend?: "up" | "down" | "neutral")
```
Prominent preformatted KPI with contextual detail. Trend indicates direction, not whether the change is good or bad.

### ProgressMeter

```text
ProgressMeter(label: string, value: number, max: number, detail?: string)
```
Labeled progress toward a positive maximum. Values above max display a full bar and retain the supplied value.

### KeyValueList

```text
KeyValueList(items: {label: string, value: string}[])
```
Readable key/value facts, specifications, booking or account details. Do not include credentials.

### Timeline

```text
Timeline(items: {title: string, date: string, description?: string, status?: "done" | "current" | "upcoming"}[])
```
Chronological milestones with explicit dates and status text. Static markers; no simulated live activity.

### KanbanBoard

```text
KanbanBoard(columns: {title: string, items: {title: string, description?: string, tag?: string}[]}[])
```
Read-only task board grouped into up to six columns. Changes are requested with normal conversation actions, not drag/drop.

### ComparisonTable

```text
ComparisonTable(title: string, columns: string[], rows: {label: string, values: string[]}[])
```
Side-by-side comparison. Each row has a label and one value for each column; cite sources separately.

### Agenda

```text
Agenda(items: {time: string, title: string, location?: string, description?: string}[])
```
Schedule or itinerary. Use supplied timezone/date in title or time fields; do not infer live calendar access.

### FileList

```text
FileList(items: {name: string, description?: string, url?: string}[])
```
Document/resource list with optional actual HTTPS links. Do not invent download links or expose local paths.

### StatusBadge

```text
StatusBadge(label: string, tone?: "neutral" | "positive" | "warning" | "negative")
```
Compact static status label with text as well as color.

### EmptyState

```text
EmptyState(title: string, description: string)
```
Explain an empty result and what the user can do next. Never fake missing data.

### QuoteBlock

```text
QuoteBlock(quote: string, attribution: string, url?: string)
```
Attributed excerpt or testimonial. Quote only supplied/source-backed text, with source URL when available.

### Checklist

```text
Checklist(items: {label: string, done: boolean, detail?: string}[])
```
Read-only completion checklist. Use CheckBoxGroup for editable selections.

### Rating

```text
Rating(label: string, value: number, max: number, detail?: string)
```
Read-only numeric rating with accessible meter. Include source/review count in detail; never invent ratings.

### ComponentTemplate

```text
ComponentTemplate(name: string, program: string, values: Record<string, string | number | boolean>)
```
Create a reusable PRESENTATION component on the fly. name identifies the layout; program is a quoted OpenUI program rooted at Stack, with @Prop("key", fallback) for scalar values. values is a JSON object. Reuse the same program variable with different values. Cards/charts/images/metrics work; templates cannot nest templates, contain forms, run code or execute actions. Use normal Form outside the template.

## React Email (44)

### EmailTemplate

```text
EmailTemplate(subject: string, previewText?: string, children: (EmailHeading | EmailText | EmailButton | EmailImage | EmailDivider | EmailLink | EmailCodeBlock | EmailCodeInline | EmailMarkdown | EmailArticle | EmailProductCard | EmailFeatureGrid | EmailFeatureList | EmailNumberedSteps | EmailCheckoutTable | EmailPricingCard | EmailTestimonial | EmailSurveyRating | EmailStats | EmailImageGrid | EmailAvatarGroup | EmailAvatarWithText | EmailList | EmailCustomerReview | EmailBentoGrid | EmailSection | EmailColumns | EmailColumn | EmailHeaderSideNav | EmailHeaderCenteredNav | EmailHeaderSocial | EmailFooterCentered | EmailFooterTwoColumn)[])
```
Root email template. Renders a live email preview with Copy HTML export. Always provide a subject line.

### EmailSection

```text
EmailSection(children: (EmailHeading | EmailText | EmailButton | EmailImage | EmailDivider | EmailLink | EmailCodeBlock | EmailCodeInline | EmailMarkdown | EmailArticle | EmailProductCard | EmailFeatureGrid | EmailFeatureList | EmailNumberedSteps | EmailCheckoutTable | EmailPricingCard | EmailTestimonial | EmailSurveyRating | EmailStats | EmailImageGrid | EmailAvatarGroup | EmailAvatarWithText | EmailList | EmailCustomerReview | EmailBentoGrid)[])
```
Groups email content into a section. Use to organize header, body, and footer areas.

### EmailColumns

```text
EmailColumns(children: EmailColumn[])
```
Multi-column row layout. Contains EmailColumn children.

### EmailColumn

```text
EmailColumn(children: (EmailHeading | EmailText | EmailButton | EmailImage | EmailDivider | EmailLink | EmailCodeBlock | EmailCodeInline | EmailMarkdown | EmailArticle | EmailProductCard | EmailFeatureGrid | EmailFeatureList | EmailNumberedSteps | EmailCheckoutTable | EmailPricingCard | EmailTestimonial | EmailSurveyRating | EmailStats | EmailImageGrid | EmailAvatarGroup | EmailAvatarWithText | EmailList | EmailCustomerReview | EmailBentoGrid)[])
```
A single column within an EmailColumns row.

### EmailHeaderSideNav

```text
EmailHeaderSideNav(logoSrc: string, logoAlt: string, logoHeight?: number, links: EmailNavLink[])
```
Header with logo on the left and navigation links on the right. Uses EmailNavLink items.

### EmailHeaderCenteredNav

```text
EmailHeaderCenteredNav(logoSrc: string, logoAlt: string, logoHeight?: number, links: EmailNavLink[])
```
Header with logo centered on top and navigation links centered below. Uses EmailNavLink items.

### EmailHeaderSocial

```text
EmailHeaderSocial(logoSrc: string, logoAlt: string, logoHeight?: number, icons: EmailSocialIcon[])
```
Header with logo on the left and social media icon links on the right. Uses EmailSocialIcon items.

### EmailNavLink

```text
EmailNavLink(text: string, href: string)
```
Navigation link item for email headers.

### EmailSocialIcon

```text
EmailSocialIcon(src: string, alt: string, href: string)
```
Social media icon link for email headers. src should be a square icon image URL.

### EmailFooterCentered

```text
EmailFooterCentered(logoSrc: string, logoAlt: string, companyName: string, tagline?: string, address: string, contact?: string, icons?: EmailSocialIcon[])
```
Centered footer with logo, company name, tagline, social icons, address, and contact info. Uses EmailSocialIcon items.

### EmailFooterTwoColumn

```text
EmailFooterTwoColumn(logoSrc: string, logoAlt: string, companyName: string, tagline?: string, address: string, contact?: string, icons?: EmailSocialIcon[])
```
Two-column footer with logo and company info on the left, social icons and address on the right. Uses EmailSocialIcon items.

### EmailHeading

```text
EmailHeading(text: string, level?: number)
```
Email heading (h1-h6). Use level 1 for main title, 2 for section headers.

### EmailText

```text
EmailText(text: string)
```
Email text paragraph for body content.

### EmailButton

```text
EmailButton(label: string, href: string, backgroundColor?: string)
```
Email call-to-action button with link.

### EmailImage

```text
EmailImage(src: string, alt: string, width?: number)
```
Email image. Use real, publicly accessible URLs.

### EmailDivider

```text
EmailDivider()
```
Horizontal divider line to separate email sections.

### EmailLink

```text
EmailLink(text: string, href: string)
```
Inline hyperlink in email content.

### EmailCodeBlock

```text
EmailCodeBlock(code: string, language?: string)
```
Syntax-highlighted code block for displaying code snippets in emails.

### EmailCodeInline

```text
EmailCodeInline(code: string)
```
Inline code snippet for embedding code within text.

### EmailMarkdown

```text
EmailMarkdown(content: string)
```
Renders markdown content as styled email HTML. Supports headings, bold, italic, links, lists, and code.

### EmailArticle

```text
EmailArticle(imageSrc: string, imageAlt: string, category?: string, title: string, description: string, buttonLabel: string, buttonHref: string, buttonColor?: string)
```
Article block with hero image, optional category label, title, description, and CTA button. Great for blog posts and newsletter articles.

### EmailProductCard

```text
EmailProductCard(imageSrc: string, imageAlt: string, category?: string, title: string, description: string, price: string, buttonLabel: string, buttonHref: string, buttonColor?: string)
```
Product showcase card with hero image, optional category, title, description, price, and buy button.

### EmailFeatureItem

```text
EmailFeatureItem(iconSrc: string, iconAlt: string, title: string, description: string)
```
Single feature item with icon, title, and description. Used inside EmailFeatureGrid or EmailFeatureList.

### EmailFeatureGrid

```text
EmailFeatureGrid(title: string, description: string, items: EmailFeatureItem[])
```
2x2 feature grid with header title, description, and four feature items each with icon, title, and description.

### EmailFeatureList

```text
EmailFeatureList(title: string, description: string, items: EmailFeatureItem[])
```
Vertical feature list with header title, description, and feature items separated by dividers. Each item has an icon, title, and description.

### EmailStepItem

```text
EmailStepItem(title: string, description: string)
```
Single numbered step with title and description. Used inside EmailNumberedSteps.

### EmailNumberedSteps

```text
EmailNumberedSteps(title: string, description: string, steps: EmailStepItem[])
```
Numbered steps list with header title, description, and sequential step items. Each step shows a numbered badge, title, and description.

### EmailCheckoutItem

```text
EmailCheckoutItem(imageSrc?: string, imageAlt?: string, name: string, quantity?: number, price: string)
```
Single checkout/cart item with optional image, name, quantity, and price. Used inside EmailCheckoutTable.

### EmailCheckoutTable

```text
EmailCheckoutTable(title?: string, items: EmailCheckoutItem[], buttonLabel: string, buttonHref: string, buttonColor?: string)
```
Checkout/cart table with product items (image, name, quantity, price) and a checkout button. Great for abandoned cart and order summary emails.

### EmailPricingFeature

```text
EmailPricingFeature(text: string)
```
Single pricing feature line item. Used inside EmailPricingCard.

### EmailPricingCard

```text
EmailPricingCard(badge?: string, price: string, period?: string, description: string, features: EmailPricingFeature[], buttonLabel: string, buttonHref: string, buttonColor?: string, note?: string, subNote?: string)
```
Pricing card with badge, price, description, feature list, CTA button, and optional note. Great for upgrade and promotional emails.

### EmailTestimonial

```text
EmailTestimonial(quote: string, avatarSrc: string, avatarAlt: string, name: string, role: string)
```
Testimonial quote with avatar, name, and role. Centered layout for social proof in emails.

### EmailSurveyRating

```text
EmailSurveyRating(question: string, description?: string, buttonColor?: string)
```
Rating survey section with a question and 1-5 numbered buttons. Great for feedback and NPS emails.

### EmailStatItem

```text
EmailStatItem(value: string, label: string)
```
Single stat with a value and label. Used inside EmailStats.

### EmailStats

```text
EmailStats(items: EmailStatItem[])
```
Horizontal stats row displaying key metrics. Each stat has a large value and a label below it.

### EmailImageGrid

```text
EmailImageGrid(title?: string, description?: string, images: EmailImage[])
```
2x2 image grid layout with optional header title and description. Pass up to 4 EmailImage items. Great for product galleries and portfolios.

### EmailAvatar

```text
EmailAvatar(src: string, alt: string, size?: number, rounded?: "full" | "md")
```
Avatar image component. Supports circular (rounded='full') or rounded-square (rounded='md') shapes, and configurable size.

### EmailAvatarGroup

```text
EmailAvatarGroup(avatars: EmailAvatar[])
```
Overlapping stacked avatar group. Pass EmailAvatar items to display them in a horizontal row with negative offset overlap.

### EmailAvatarWithText

```text
EmailAvatarWithText(avatarSrc: string, avatarAlt: string, name: string, role: string, href?: string)
```
Avatar with name and role text beside it. Optionally wraps in a link. Great for author attribution or team member display.

### EmailListItem

```text
EmailListItem(title: string, description: string)
```
Data-only list item with title and description. Used as a child inside EmailList.

### EmailList

```text
EmailList(title?: string, items: EmailListItem[])
```
Numbered list with circular number badges and item title + description. Pass EmailListItem children. Great for feature lists, how-it-works sections, and top-N lists.

### EmailCustomerReview

```text
EmailCustomerReview(title?: string, totalReviews: number, rating5: number, rating4: number, rating3: number, rating2: number, rating1: number, buttonLabel?: string, buttonHref?: string, buttonColor?: string)
```
Customer review summary with star rating distribution bars showing percentages for each rating (1-5). Includes total review count and optional CTA button to write a review.

### EmailBentoItem

```text
EmailBentoItem(imageSrc: string, imageAlt: string, title: string, description: string)
```
Data-only bento grid item with image, title, and description. Used as a child inside EmailBentoGrid.

### EmailBentoGrid

```text
EmailBentoGrid(heroTitle: string, heroDescription: string, heroLinkText?: string, heroLinkHref?: string, heroImageSrc: string, heroImageAlt: string, items: EmailBentoItem[])
```
Bento grid layout with a dark hero section (title, description, link, image) on top and a row of product cards below. Pass EmailBentoItem children for the bottom row. Great for marketing and product showcase emails.

## Reusable template example

Forms and actions stay in the main program. Template values are strings, finite numbers or booleans; templates cannot nest.

```text
root = Stack([ComponentTemplate("Tasks", tile, {label:"Tasks",value:"42"}), ComponentTemplate("Projects", tile, {label:"Projects",value:"3"})])
tile = "root = Stack([MetricCard(@Prop(\"label\", \"Label\"), @Prop(\"value\", \"0\"))])"
```
## Worked compositions

Syntax examples only; replace all sample facts and URLs.

### Sourced visual results

```text
root = Stack([TextContent("Two supplied photo candidates", "large-heavy"), ImageCarousel("Compare the photographs", photos), TextContent("Compare the framing, then open the original source for details.")])
photos = [{title:"Candidate A",imageUrl:"https://images.example.com/a.jpg",alt:"Replace with the actual subject of photo A",description:"Replace with a fact from result A",sourceUrl:"https://example.com/a",sourceName:"Source A"},{title:"Candidate B",imageUrl:"https://images.example.com/b.jpg",alt:"Replace with the actual subject of photo B",description:"Replace with a fact from result B",sourceUrl:"https://example.com/b",sourceName:"Source B"}]
```

### Report with overview and detailed evidence

```text
root = Stack([Dashboard("Three-day progress", "Illustrative supplied snapshot, Monday to Wednesday. Units: completed tasks.", [summary, views], "one")])
summary = DashboardSection("42 tasks completed", [MetricCard("Completed", "42", "10 + 14 + 18 tasks"), ProgressMeter("Target progress", 42, 50, "8 tasks remain against the supplied target")])
views = Tabs([TabItem("trend", "Daily trend", [chart, TextContent("Daily completions increased from 10 to 18.")]), TabItem("details", "Source figures", [table])])
chart = ChartJS("Completed tasks per day", "bar", ["Monday", "Tuesday", "Wednesday"], [{label:"Tasks",data:[10,14,18]}], false, false, "Illustrative values supplied for this example.")
table = Table([Col("Day", ["Monday", "Tuesday", "Wednesday"]), Col("Completed tasks", [10,14,18], "number")])
```

### Missing preferences with a known editable default

```text
root = Stack([TextContent("Tailor the plan", "large-heavy"), TextContent("Your three-person group is filled in. Add the remaining preferences to continue."), form])
$people = "3"
form = Form("trip_preferences", Buttons([Button("Plan with these preferences", @ToAssistant("Use these preferences to plan my trip"))]), [group, pace, interests])
group = FormControl("People", Input("people", "Group size", "number", {required:true,numeric:true,min:1,max:30}, $people))
pace = FormControl("Pace", Select("pace", [SelectItem("relaxed", "Relaxed"), SelectItem("active", "Active")], "Choose a pace", {required:true}))
interests = FormControl("Interests", TextArea("interests", "What would you enjoy?", 3), "Optional; leave blank if you have no preference")
```

### Comparison with a clear tradeoff and secondary detail

```text
root = Stack([TextContent("Choose the workshop format", "large-heavy"), TextContent("In this illustrative brief, the short session suits orientation; the longer session includes practice."), comparison, details, Buttons([Button("Help me choose", @ToAssistant("Help me choose a workshop format using my constraints"))])])
comparison = ComparisonTable("Supplied options", ["Orientation", "Hands-on"], [{label:"Duration",values:["30 minutes","90 minutes"]},{label:"Format",values:["Overview and questions","Overview, practice and questions"]}])
details = Accordion([AccordionItem("scope", "What these options include", [TextContent("These are illustrative options from a supplied brief. Scheduling and availability are not confirmed.")])])
```
