function padTo2Digits(num) {
  return num.toString().padStart(2, '0');
}

function convertMsToTime(milliseconds) {
  let seconds = Math.floor(milliseconds / 1000);
  let minutes = Math.floor(seconds / 60);

  seconds = seconds % 60;
  minutes = minutes % 60;

  return `${padTo2Digits(minutes)}:${padTo2Digits(seconds)}`;
}

function shortenUrl(url, append) {
  var shortenedUrl = url.replace('https://', '').replace('http://', '').replace('www.', '');
  if (shortenedUrl.length > 18 && append) {
    shortenedUrl = shortenedUrl.slice(0, 18) + '...';
  }
  return shortenedUrl;
}

function getFavicon(url, size) {
  return 'https://www.google.com/s2/favicons?domain=' + url + '&sz=' + size;
}


nunjucksEnv.addFilter('shortenUrl', shortenUrl);
nunjucksEnv.addFilter('getFavicon', getFavicon);