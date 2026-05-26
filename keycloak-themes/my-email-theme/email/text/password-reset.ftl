<#assign token = link?keep_after("key=")?keep_before("&")>
<#assign frontendUrl = properties.frontendUrl!"http://158.160.90.90:3000">
<#assign resetUrl = "${frontendUrl}/reset-password/${token}">
Reset your password: ${resetUrl}

This link will expire within 12 hours.
If you didn't request this, please ignore this email.
