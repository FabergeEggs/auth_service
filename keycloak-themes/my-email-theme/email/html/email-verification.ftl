<#assign token = link?keep_after("key=")?keep_before("&")>
<#assign frontendUrl = properties.frontendUrl!"http://158.160.90.90:3000">
<#assign verifyUrl = "${frontendUrl}/verify-email/${token}">
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Verify your email</title>
</head>
<body>
  <p>Verify your email:</p>
  <p><a href="${verifyUrl}">${verifyUrl}</a></p>
  <p>This link will expire within 12 hours.</p>
</body>
</html>
