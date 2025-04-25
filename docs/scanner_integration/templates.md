# Template Authoring Guide for OpenZeppelin Inspector Compatibility

This document provides detailed guidance for **scanner (static analyzer) developers** who want their tools to be fully
compatible with the **OpenZeppelin Inspector** static analysis orchestration framework. By following these conventions,
your scanner’s findings will be rendered clearly and consistently within Inspector, maximizing usability and
integration.

---

## 1. **Template Structure**

A template is a **dictionary (JSON or YAML)** that defines how your scanner’s findings are rendered by Inspector. It
uses [Python string.Template](https://docs.python.org/3/library/string.html#template-strings) syntax (`$variable`).

### **Example Template Skeleton**

```json
{
  "title": "Potential issue in $file_name",
  "title-single-instance": "Issue in $file_name",
  "title-multiple-instance": "Multiple issues in $file_name",
  "opening": "We found an issue in your codebase.",
  "body": "This issue affects $total_files file(s) and $total_instances instance(s).",
  "body-single-file-single-instance": "...",
  "body-single-file-multiple-instance": "...",
  "body-multiple-file-single-instance": "...",
  "body-multiple-file-multiple-instance": "...",
  "body-list-item": "* On line $instance_line of `$file_name`",
  "body-list-item-single-file": "...",
  "body-list-item-multiple-file": "...",
  "body-list-item-always": "...",
  "body-list-item-intro": "Instances:",
  "closing": "Please review the above findings."
}
```

---

## 2. **Template Keys and Their Purpose**

### **A. Title Section**

- **`title`**: Fallback title for the finding.
- **`title-single-instance`**: Title when only one instance is found.
- **`title-multiple-instance`**: Title when multiple instances are found.

### **B. Opening Section**

- **`opening`**: (Optional) Introductory text at the start of the finding.

### **C. Body Section**

- **`body`**: Generic body text.
- **`body-<files>-file-<instances>-instance`**: More specific body templates, where `<files>` is `single` or
  `multiple`, and `<instances>` is `single` or `multiple`.
    - Example: `body-single-file-multiple-instance`
- **`body-list-item`**: Template for each instance in the list.
- **`body-list-item-single-file`**: Used when only one file is affected.
- **`body-list-item-multiple-file`**: Used when multiple files are affected.
- **`body-list-item-always`**: If present, always used for instance lines.
- **`body-list-item-intro`**: (Optional) Intro text before the instance list.

### **D. Closing Section**

- **`closing`**: (Optional) Text to append at the end of the finding.

---

## 3. **Required vs. Optional Keys**

- **Required:**
    - At least one of `title`, `title-single-instance`, or `title-multiple-instance`.
    - At least one of `body`, `body-<files>-file-<instances>-instance`, or `body-list-item`.
- **Optional:**
    - `opening`
    - `closing`
    - `body-list-item-intro`
    - More specific body or list item templates for fine-tuned control.

---

## 4. **Template Substitution Variables**

The following variables can be used in any template string. Inspector will replace them with context-specific values
from your scanner’s findings.

### **General Variables**

- `$file_name`: Name of the affected file.
- `$codebase_path`: Root path of the codebase.
- `$total_instances`: Total number of instances found.
- `$total_files`: Number of files affected.
- `$total_lines`: Total number of lines affected.

### **Instance-Specific Variables** (for list items)

- `$instance_line`: Starting line number of the instance.
- `$instance_line_start`: Starting line number.
- `$instance_line_end`: Ending line number.
- `$instance_line_link`: Link to the specific line or range in the file.
- `$instance_line_count`: Number of lines in the instance.

### **Metavariables**

- Any custom variables your scanner provides as `metavars` in the finding instance's `extra` field will be
  available for substitution **in instance-specific templates** (list items).
- Metavariables are not available in global templates like `title`, `opening`, or `body` as they are bound to specific instances.
- Use metavariables to include instance-specific details that aren't captured by the standard variables.

---

## 5. **Template Resolution Logic**

- Inspector **selects the most specific template available** for each section.
    - For the body, it tries `body-<files>-file-<instances>-instance` first, then falls back to `body`, then to
      an empty string.
    - For list items, it tries `body-list-item-always`, then `body-list-item-<files>-file`, then
      `body-list-item`, then a default.
- If a template key is missing, Inspector uses a built-in default.

---

## 6. **Best Practices for Scanner Authors**

- **Be explicit**: Provide as many specific templates as needed for your scanner’s use case.
- **Use clear, actionable language**: Help users understand what the issue is and where to find it.
- **Include links**: Use `$instance_line_link` to make findings navigable.
- **Test your templates**: Try with single/multiple files and instances to ensure all cases are covered.
- **Document custom metavariables**: If your scanner outputs custom variables, document them for template authors and
  users.

---

## 7. **Example: Minimal Template**

```json
{
  "title": "Issue in $file_name",
  "body": "There is an issue on line $instance_line of `$file_name`.",
  "body-list-item": "* Line $instance_line: see details.",
  "closing": "Please address this issue."
}
```

---

## 8. **Example: Advanced Template**

```json
{
  "title-single-instance": "Critical issue in $file_name",
  "title-multiple-instance": "Multiple issues in $file_name",
  "opening": "Automated analysis detected the following:",
  "body-single-file-single-instance": "A single issue was found in `$file_name` at line $instance_line.",
  "body-single-file-multiple-instance": "Multiple issues were found in `$file_name`.",
  "body-multiple-file-multiple-instance": "Issues were found across $total_files files.",
  "body-list-item": "* [Line $instance_line]($instance_line_link) in $file_name",
  "body-list-item-intro": "Affected locations:",
  "closing": "Review and remediate as appropriate."
}
```

---

## 9. **Troubleshooting**

- **Missing variables**: If a variable is not available, it will be left blank in the output.
- **Syntax errors**: Use `$variable` for substitution. `${variable}` is also supported by `string.Template`.
- **Fallbacks**: If a specific template is missing, Inspector will use the next most generic template or a built-in
  default.

---

## 10. **Summary Table of Template Keys**

| Key                                        | Purpose/When Used                           | Required |
|--------------------------------------------|---------------------------------------------|----------|
| `title`                                | Generic finding title                       | Yes*     |
| `title-single-instance`                | Title for single instance                   | No       |
| `title-multiple-instance`              | Title for multiple instances                | No       |
| `opening`                              | Opening paragraph                           | No       |
| `body`                                 | Generic body                                | Yes*     |
| `body-single-file-single-instance`     | Body for 1 file, 1 instance                 | No       |
| `body-single-file-multiple-instance`   | Body for 1 file, multiple instances         | No       |
| `body-multiple-file-single-instance`   | Body for multiple files, 1 instance         | No       |
| `body-multiple-file-multiple-instance` | Body for multiple files, multiple instances | No       |
| `body-list-item`                       | Template for each instance in the list      | Yes*     |
| `body-list-item-single-file`           | List item for single file                   | No       |
| `body-list-item-multiple-file`         | List item for multiple files                | No       |
| `body-list-item-always`                | Always used for list items if present       | No       |
| `body-list-item-intro`                 | Intro before instance list                  | No       |
| `closing`                              | Closing paragraph                           | No       |

\*At least one of the marked keys must be present.

---

## 11. **Further Reading**

- [Python string.Template documentation](https://docs.python.org/3/library/string.html#template-strings)

---

**By following this guide, your scanner’s output will be fully compatible with the OpenZeppelin Inspector, ensuring that
your findings are rendered clearly and effectively within the Inspector ecosystem.**
