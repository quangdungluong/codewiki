def format_message(data: dict[str, str]) -> str:
    parts = []
    for key, value in data.items():
        if key == "file_tree":
            parts.append(f"<file_tree>\n{value}\n</file_tree>")
        elif key == "readme":
            parts.append(f"<readme>\n{value}\n</readme>")
        elif key == "explanation":
            parts.append(f"<explanation>\n{value}\n</explanation>")
        elif key == "diagram":
            parts.append(f"<diagram>\n{value}\n</diagram>")
        elif key == "component_mapping":
            parts.append(f"<component_mapping>\n{value}\n</component_mapping>")
        elif key == "instructions":
            parts.append(f"<instructions>\n{value}\n</instructions>")

    return "\n\n".join(parts)
