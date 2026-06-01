<#assign token = link?keep_after("key=")?keep_before("&")>
<p><a href="http://localhost:3000/reset-password/${token}">Reset your password</a></p>

<p>This link will expire within 12 hours.</p>
<p>If you didn't request this, please ignore this email.</p>
