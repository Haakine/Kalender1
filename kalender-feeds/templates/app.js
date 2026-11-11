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
  var now = new Date();

  function text(el, value) { if (el) { el.textContent = value; } }
  function trimDot(value) { return value.replace(/\.$/, ""); }

  // Heldagsdatoer ("2027-02-24") tolkes som lokal dato, ikke UTC.
  function parseDay(value) {
    var p = value.split("-");
    return new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
  }

  // «Alle hendelser» viser full tittel (kilden trengs der), de andre kortene den korte.
  function normaliser(feedId) {
    return function (raw) {
      var title = feedId === "alle" ? raw.title : raw.short;
      if (raw.allDay) {
        return { title: title, allDay: true, raw: raw.start, start: parseDay(raw.start), end: parseDay(raw.end) };
      }
      var moment = new Date(raw.start);
      return { title: title, allDay: false, raw: raw.start, start: moment, end: moment };
    };
  }

  function isUpcoming(e) {
    return e.allDay ? e.end.getTime() > now.getTime() : e.start.getTime() >= now.getTime();
  }

  function isOngoing(e) {
    return e.allDay && e.start.getTime() <= now.getTime();
  }

  function when(e) {
    if (!e.allDay) { return dateFmt.format(e.start) + " kl. " + timeFmt.format(e.start); }
    var last = new Date(e.end.getTime());
    last.setDate(last.getDate() - 1); // slutten er eksklusiv
    if (last.getTime() <= e.start.getTime()) { return dateFmt.format(e.start); }
    return dateFmt.format(e.start) + " til " + dateFmt.format(last);
  }

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

    var upcoming = (events[id] || []).map(normaliser(id)).filter(isUpcoming).sort(function (a, b) {
      return a.start.getTime() - b.start.getTime();
    });

    if (upcoming.length === 0) {
      text(card.querySelector(".js-next"), "Ingen kommende datoer i feeden akkurat nå.");
      return;
    }

    var first = upcoming[0];
    var ongoing = isOngoing(first);
    var shown = ongoing ? now : first.start;
    text(card.querySelector(".js-day"), trimDot(dayFmt.format(shown)));
    text(card.querySelector(".js-month"), trimDot(monthFmt.format(shown)));
    text(card.querySelector(".js-next"), (ongoing ? "Pågår: " : "Neste: ") + first.title + ", " + when(first));

    var list = card.querySelector(".js-upcoming");
    if (list) {
      upcoming.slice(0, 10).forEach(function (e) {
        var li = document.createElement("li");
        var time = document.createElement("time");
        time.setAttribute("datetime", e.raw);
        time.textContent = e.allDay ? dateFmt.format(e.start) : dateFmt.format(e.start) + " " + timeFmt.format(e.start);
        var title = document.createElement("span");
        title.textContent = e.title;
        li.appendChild(time);
        li.appendChild(title);
        list.appendChild(li);
      });
    }
  });
})();
