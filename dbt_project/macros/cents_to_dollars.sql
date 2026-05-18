-- cents_to_dollars.sql
-- Reusable macro for formatting currency columns.
-- Demonstrates dbt macro pattern for interview discussion.

{% macro cents_to_dollars(column_name, precision=2) %}
    round(cast({{ column_name }} as decimal(12, 2)), {{ precision }})
{% endmacro %}
