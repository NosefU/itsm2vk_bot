import string

md_notification = string.Template(
    "*#$idx*\n\n"
    "⭐ $priority\n"
    "👤 $family_name $name $parent_name\n"
    "🏭 $org_unit\n"
    "📆 $creation_date\n\n"
    # "🔗 [Инцидент в ITSM]($link)\n\n"
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

md_mon_notification = string.Template(
    "$priority_emoji *$server*\n"
    "_$registration_date _\n\n"
    "*`📖 $description`*\n"
)
