<html>
<body>
    <#assign token = link?split("key=")[1]>
    <p>Please verify your email by clicking the link below:</p>
    <p><a href="http://localhost:3000/verify-email/${token}">Verify Email</a></p>
    <p>Or copy this link: http://localhost:3000/verify-email/${token}</p>
</body>
</html>
