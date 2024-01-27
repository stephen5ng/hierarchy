<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="/static/styles.css">

     <style>
    </style>
    <script src="/static/script.js" defer></script>
</head>
<body>
    <div class="tile" id="previous-guesses"></div>
    <div id="container">
        <div class="tile" id="score"></div>
        <div id="start-line"></div>
        <span id="falling-x">{{next_tile}}</span>
        <div class="tile" id="tiles">{{tiles}}</div>
    </div> 
    <form autocomplete="off" id="guess-form">
        <input type="text" class="tile" id="guess" autofocus style="text-transform:uppercase">
        <button id="play" type="submit">PLAY</button>
    </form>
    <span id="status"></span>
    <br/>
    <span id="errors"></span>
</body>
</html>