<#assign token = link?keep_after("key=")?keep_before("&")>
<#assign frontendUrl = properties.frontendUrl!"http://158.160.90.90:3000">
<#if requiredActions?seq_contains("UPDATE_PASSWORD")>
<#assign actionUrl = "${frontendUrl}/reset-password/${token}">
Reset your password: ${actionUrl}

This link will expire within 12 hours.
If you didn't request this, please ignore this email.
<#else>
<#assign actionUrl = "${frontendUrl}/verify-email/${token}">
Verify your email: ${actionUrl}

This link will expire within 12 hours.
</#if>
