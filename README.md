# Markdown Syntax Reference

A reference for the Markdown syntax supported by **Confetti** when converting
to and from Confluence XHTML.

# Basic Syntax

These elements are part of John Gruber's original Markdown design document.

## Headings

To create a heading, prefix with as many number of `#` as the heading level.

```markdown
# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
```

## Paragraphs

To create paragraphs, use a blank line to separate one or more lines of text.

Example: I really like using Markdown.

## Line Breaks

To create a line break (new line), end a line with two or more spaces, then type return.

Example: This is the first line.  
And this is the second line.

If your Markdown app supports HTML, you can use the `<br>` HTML tag instead of two spaces.

## Emphasis

You can add emphasis by making text bold or italic.

### Bold

Add two asterisks or underscores before and after a word or phrase.

Example: I just love **bold text**.

### Italic

Add one asterisk or underscore before and after a word or phrase.

Example: Italicized text is the *cat's meow*.

### Bold and Italic

To emphasize text with bold and italics at the same time, wrap in triple asterisks or underscores.

Example: This text is ***really important***.

## Blockquotes

To create a blockquote, add a > in front of a paragraph.

> Dorothy followed her through many of the beautiful rooms in her castle.

Blockquotes can contain multiple paragraphs. Add a > on the blank lines between the paragraphs.

> Dorothy followed her through many of the beautiful rooms in her castle.
>
> The Witch bade her clean the pots and kettles and sweep the floor and keep the fire fed with wood.

Blockquotes can be nested. Add a >> in front of the paragraph you want to nest.

> Dorothy followed her through many of the beautiful rooms in her castle.
>
>> The Witch bade her clean the pots and kettles and sweep the floor and keep the fire fed with wood.

Blockquotes can contain certain other Markdown formatted elements.

> #### The quarterly results look great!
>
> - Revenue was off the chart.
> - Profits were higher than ever.
>
>  *Everything* is going according to **plan**.

## Lists
You can organize items into ordered and unordered lists.

### Ordered Lists

To create an ordered list, add line items with numbers followed by periods. The numbers don’t have to be in numerical order, but the list should start with the number one.

1. First item
2. Second item
3. Third item
4. Fourth item

### Unordered Lists

To create an unordered list, add dashes (-), asterisks (*), or plus signs (+) in front of line items.

- First item
- Second item
- Third item
- Fourth item

### Adding Elements in Lists

To add another element in a list while preserving the continuity of the list, indent the element four spaces or one tab.

* This is the first list item.
* Here's the second list item.

    I need to add another paragraph below the second list item.

* And here's the third list item.

## Code

### Inline Code

To denote a word or phrase as code, enclose it in backticks (`).

Example: At the command prompt, type `nano`.

### Code Blocks

To create code blocks, indent every line of the block by at least four spaces or one tab.

    def hello():
        print("Hello, world!")

## Links

To create an inline link, use the `[text](url)` syntax.

Example: My favorite search engine is [Duck Duck Go](https://duckduckgo.com).

# Extended Syntax

These elements are a superset of the basic Markdown syntax.
They are supported by various Markdown implementations as extensions to the original specification.

## Tables

To add a table, use three or more hyphens (---) to create each column’s header, and use pipes (|) to separate each column.

| Syntax      | Description |
| ----------- | ----------- |
| Header      | Title       |
| Paragraph   | Text        |

## Fenced Code Blocks

Instead of indenting every line, use three backlicks (```).
You can optionally specify a language for syntax highlighting.

```python
def hello():
    print("Hello, world!")
```

## Strikethrough

You can strikethrough words by putting a horizontal line through the center of them.

Example: ~~The world is flat.~~ We now know that the world is round.

## Task Lists

Task lists (also referred to as checklists and todo lists) allow you to create a list of items with checkboxes.

- [x] Write the press release
- [ ] Update the website
- [ ] Contact the media

# Custom Syntax

Extensions specific to Confetti.

## Tables with Merged Cells

Use `<` and `^` markers to represent merged cells.

### Colspan example

| A | B | C |
| --- | --- | --- |
| merged | < | C1 |
| A2 | B2 | C2 |

Rendered output looks like this:

<table>
<tr><th>A</th><th>B</th><th>C</th></tr>
<tr><td colspan="2">merged</td><td>C1</td></tr>
<tr><td>A2</td><td>B2</td><td>C2</td></tr>
</table>

### Rowspan example

| A | B |
| --- | --- |
| tall | B1 |
| ^ | B2 |

Rendered output looks like this:

<table>
<tr><th>A</th><th>B</th></tr>
<tr><td rowspan="2">tall</td><td>B1</td></tr>
<tr><td>B2</td></tr>
</table>

### Combined colspan + rowspan

| A | B | C |
| --- | --- | --- |
| big | < | C1 |
| ^ | < | C2 |

Rendered output looks like this:

<table>
<tr><th>A</th><th>B</th><th>C</th></tr>
<tr><td colspan="2" rowspan="2">big</td><td>C1</td></tr>
<tr><td>C2</td></tr>
</table>
