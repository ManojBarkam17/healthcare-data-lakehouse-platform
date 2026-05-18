-- generate_surrogate_key.sql
-- Creates a deterministic surrogate key from one or more columns.
-- Useful when dbt_utils.generate_surrogate_key isn't available.

{% macro generate_surrogate_key(field_list) %}
    md5(concat_ws('|',
        {% for field in field_list %}
            coalesce(cast({{ field }} as varchar), '_null_')
            {% if not loop.last %}, {% endif %}
        {% endfor %}
    ))
{% endmacro %}
