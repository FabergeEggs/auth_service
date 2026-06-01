<#assign token = link?keep_after("key=")?keep_before("&")>
<#if requiredActions?seq_contains("UPDATE_PASSWORD")>
<p><a href="http://localhost:3000/reset-password/${token}">Reset your password</a></p>

<p>This link will expire within 12 hours.</p>
<p>If you didn't request this, please ignore this email.</p>
<#else>
<p><a href="http://localhost:3000/verify-email/${token}">Verify your email</a></p>

<p>This link will expire within 12 hours.</p>
</#if>
