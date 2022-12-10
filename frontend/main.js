htmx.defineExtension('qr-form-controller', {
  onEvent: function (name, evt) {
      if (name === "htmx:configRequest" && evt.detail.elt.id === "new-qr-form") {
        evt.detail.headers['Content-Type'] = "application/json";
        evt.detail.elt.elements[7].classList.add("disabled");
        evt.detail.elt.lastElementChild.classList.remove("d-none");
        
      }

      if (name === "htmx:afterRequest" && evt.detail.elt.id === "new-qr-form") {
        animateCSS('#form-row', 'fadeOut').then((message) => {
          evt.target.lastElementChild.classList.add("d-none");
          evt.target.parentElement.parentElement.classList.add("d-none");
          console.log(evt.target.parentElement.parentElement);
          evt.target[7].classList.remove("disabled");
          animateCSS('#new-qr', 'fadeIn')
          document.querySelector("#new-qr").classList.remove("d-none");
          document.querySelector("#new-qr-form").reset();
        });
      }
  },
  
  encodeParameters : function(xhr, parameters, elt) {
      xhr.overrideMimeType('text/json');
      console.log(parameters);
      let parsedParameters = parseDotKeysAsNestedObjects(parameters);
      return (JSON.stringify(parsedParameters));
  }
});

function parseDotKeysAsNestedObjects(obj) {
  const result = {};
  Object.keys(obj).forEach((key) => {
    const value = obj[key];
    const parts = key.split('.');
    let current = result;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!current[part]) {
        current[part] = {};
      }
      current = current[part];
    }
    current[parts[parts.length - 1]] = value;
  });
  return result;
}

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

htmx.logger = function(elt, event, data) {
  console.log(event, elt, data);
}


htmx.defineExtension('qr-preview', {
  onEvent: function (name, evt) {
    if (name === "htmx:configRequest") {
      let elt = evt.detail.elt.closest("#new-qr-form");
      let previewParams = {};
      let inputs = [];
      findTagInChildrenRecursive(elt, "input", inputs);
      findTagInChildrenRecursive(elt, "select", inputs);
      for (key in inputs) {
        if (inputs[key].name) {
          previewParams[inputs[key].name] = inputs[key].value;
        }
      }
      evt.detail.path += "?" + objectToUrlParamsRecursive(previewParams);
      console.log(evt.detail.path);
    }
  },
});

function findTagInChildrenRecursive(elt, tag, result) {
  if (elt.tagName.toLowerCase() === tag) {
    result.push(elt);
  }
  for (var i = 0; i < elt.children.length; i++) {
    findTagInChildrenRecursive(elt.children[i], tag, result);
  }
}

function objectToUrlParamsRecursive(obj, prefix) {
  var str = [];
  for(var p in obj) {
    if (obj.hasOwnProperty(p)) {
      var k = prefix ? prefix + "[" + p + "]" : p, v = obj[p];
      str.push((v !== null && typeof v === "object") ?
        objectToUrlParamsRecursive(v, k) :
        encodeURIComponent(k) + "=" + encodeURIComponent(v));
    }
  }
  return str.join("&");
}

const animateCSS = (element, animation, prefix = 'animate__') =>
  // We create a Promise and return it
  new Promise((resolve, reject) => {
    const animationName = `${prefix}${animation}`;
    const node = document.querySelector(element);

    node.classList.add(`${prefix}animated`, animationName);

    // When the animation ends, we clean the classes and resolve the Promise
    function handleAnimationEnd(event) {
      event.stopPropagation();
      node.classList.remove(`${prefix}animated`, animationName);
      resolve('Animation ended');
    }

    node.addEventListener('animationend', handleAnimationEnd, {once: true});
  });


document.addEventListener("click", function(event) {
  if (event.target.id === "create-new-qr-btn") {
    animateCSS('#new-qr', 'fadeOut');
    let new_qr = document.querySelector("#new-qr");
    new_qr.removeChild(new_qr.lastElementChild);
    animateCSS("#form-row", "fadeIn");
    document.querySelector("#form-row").classList.remove("d-none");
  }
});