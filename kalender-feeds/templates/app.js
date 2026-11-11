(function () {
  "use strict";

  var events = {};
  try {
    events = JSON.parse(document.getElementById("events").textContent);
  } catch (e) { /* siden fungerer uten datoer, med nedlastingslenker */ }

  var dateFmt = new Intl.DateTimeFormat("nb-NO", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
  var timeFmt = new Intl.DateTimeFormat("nb-NO", { hour: "2-digit", minute: "2-digit" });
  var monthFmt = new Intl.DateTimeFormat("nb-NO", { month: "short" });
  var dayFmt = new Intl.DateTimeFormat("nb-NO", { day: "numeric" });

  var canSubscribe = location.protocol === "https:" || location.protocol === "http:";

  function text(el, value) { if (el) { el.textContent = value; } }
  // Kortene har allerede kilden i overskriften, så «Norges Bank: » foran tittelen er overflødig.
  function shortTitle(title) { return title.replace(/^[^:]+:\s*/, ""); }

  Array.prototype.forEach.call(document.querySelectorAll("[data-feed]"), function (card) {
    var id = card.getAttribute("data-feed");
    var icsUrl = new URL("ics/" + id + ".ics", location.href);

    var subscribe = card.querySelector(".js-subscribe");
    if (subscribe && canSubscribe) {
      subscribe.href = "webcal://" + icsUrl.host + icsUrl.pathname;
      subscribe.hidden = false;
    }

    var copy = card.querySelector(".js-copy");
    if (copy) {
      if (canSubscribe && navigator.clipboard) {
        copy.addEventListener("click", function () {
          navigator.clipboard.writeText(icsUrl.href).then(
            function () { copy.textContent = "Lenke kopiert"; },
            function () { copy.textContent = "Kunne ikke kopiere"; }
          );
        });
      } else {
        copy.hidden = true;
      }
    }

    var now = Date.now();
    var upcoming = (events[id] || []).filter(function (e) { return Date.parse(e.start) >= now; });

    if (upcoming.length === 0) {
      text(card.querySelector(".js-next"), "Ingen kommende datoer i feeden akkurat nå.");
      return;
    }

    var first = upcoming[0];
    var firstDate = new Date(first.start);
    text(card.querySelector(".js-day"), dayFmt.format(firstDate).replace(/\.$/, ""));
    text(card.querySelector(".js-month"), monthFmt.format(firstDate).replace(/\.$/, ""));
    text(card.querySelector(".js-next"), "Neste: " + shortTitle(first.title) + ", " + dateFmt.format(firstDate) + " kl. " + timeFmt.format(firstDate));

    var list = card.querySelector(".js-upcoming");
    if (list) {
      upcoming.slice(0, 8).forEach(function (e) {
        var d = new Date(e.start);
        var li = document.createElement("li");
        var time = document.createElement("time");
        time.setAttribute("datetime", e.start);
        time.textContent = dateFmt.format(d) + " " + timeFmt.format(d);
        var title = document.createElement("span");
        title.textContent = shortTitle(e.title);
        li.appendChild(time);
        li.appendChild(title);
        list.appendChild(li);
      });
    }
  });
})();
