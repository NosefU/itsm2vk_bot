import string

md_notification = string.Template(
    "*#$idx*\n\n"
    "⭐ $priority\n"
    "👤 $family_name $name $parent_name\n"
    "🏭 $org_unit\n"
    "📆 $creation_date\n"
    "🔗 [Инцидент в ITSM]($link)\n\n"
    "🪧 *Описание*\n"
    "$subject\n\n"
    "📖 *Подробно*\n"
    "$description"
)

md_description = string.Template(
    "👤 $family_name $name $parent_name\n"
    "🏭 $org_unit\n"
    "📆 $creation_date\n"
    "⚙ `$device`\n\n"
    "✏️ $description"
)
