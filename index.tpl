<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="/static/styles.css">

     <style>
    </style>
    <script src="/static/script.js" defer></script>
</head>
<body>
    <div id="container">
        <div id="start-line"></div>
        <span id="falling-x">{{next_tile}}</span>
    </div> 
    <span id="tiles">{{tiles}}</span>
    <form autocomplete="off" id="guess-form">
        <input type="text" id="guess" style="text-transform:uppercase">
        <button type="submit">PLAY</button>
    </form>
    <span id="status">status</span>
    <br/>
    <span id="errors"></span>
</body>
</html>