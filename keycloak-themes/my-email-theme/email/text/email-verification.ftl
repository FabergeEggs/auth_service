<#assign token = link?keep_after("key=")?keep_before("&")>
<#assign frontendUrl = properties.frontendUrl!"http://158.160.90.90:3000">
<#assign verifyUrl = "${frontendUrl}/verify-email/${token}">
Verify your email: ${verifyUrl}

This link will expire within 12 hours.
