/* Amorae feed — vertical short-video player.
 *
 * Design notes worth knowing before changing anything here:
 *
 *  - Scroll and snap physics belong to the BROWSER (CSS scroll-snap), not to
 *    JS. Hand-rolled swipe handling is what makes web feeds feel wrong on
 *    iOS, because it fights momentum scrolling and rubber-banding.
 *  - Autoplay only works muted. Every mobile browser blocks audio until a
 *    real user gesture, so we start muted and the first tap on the speaker
 *    unmutes for the whole session.
 *  - Only ONE video is ever playing, and only videos near the viewport hold
 *    a network connection. Otherwise a long scroll opens dozens of
 *    simultaneous range requests and the CDN bill goes with it.
 */
(function () {
  "use strict";

  var feed = document.getElementById("feed");
  var app = document.querySelector(".feed-app");
  var sentinel = document.getElementById("feed-sentinel");
  if (!feed) return;

  var PRELOAD_RADIUS = 2; // videos either side of the visible one to buffer
  var isUnmuted = false;
  var isLoading = false;
  var current = null;

  /* ---------------------------------------------------------------- utils */

  function compact(n) {
    n = Number(n) || 0;
    if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
    if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "K";
    return String(n);
  }

  function reels() {
    return Array.prototype.slice.call(feed.querySelectorAll(".reel"));
  }

  /* --------------------------------------------------------- media control */

  // Attaching src lazily is the difference between 3 open connections and 30.
  function ensureSource(reel) {
    var video = reel.querySelector(".reel-video");
    if (video && !video.src && video.dataset.src) {
      video.src = video.dataset.src;
      video.preload = "auto";
    }
  }

  function releaseSource(reel) {
    var video = reel.querySelector(".reel-video");
    if (video && video.src && video.dataset.src) {
      video.removeAttribute("src");
      video.load(); // drops the buffer; without this Safari keeps it alive
    }
  }

  function buffer(activeIndex) {
    var all = reels();
    all.forEach(function (reel, i) {
      if (Math.abs(i - activeIndex) <= PRELOAD_RADIUS) ensureSource(reel);
      else releaseSource(reel);
    });
  }

  function play(reel) {
    if (!reel || reel === current) return;
    if (current) pause(current, true);

    current = reel;
    var all = reels();
    buffer(all.indexOf(reel));
    ensureSource(reel);

    var video = reel.querySelector(".reel-video");
    if (!video) return;
    video.muted = !isUnmuted;
    video.currentTime = 0;
    reel.classList.remove("is-paused");

    var attempt = video.play();
    if (attempt && attempt.catch) {
      attempt.catch(function () {
        // Autoplay refused (some browsers refuse even muted until the user
        // has interacted with the document). Show the play affordance
        // instead of leaving a silent black frame.
        reel.classList.add("is-paused");
      });
    }
  }

  function pause(reel, rewind) {
    var video = reel && reel.querySelector(".reel-video");
    if (!video) return;
    video.pause();
    if (rewind) video.currentTime = 0;
  }

  function toggle(reel) {
    var video = reel.querySelector(".reel-video");
    if (!video) return;
    if (video.paused) {
      video.play();
      reel.classList.remove("is-paused");
    } else {
      video.pause();
      reel.classList.add("is-paused");
    }
  }

  /* ------------------------------------------------------------- observers */

  // 0.6 means "most of this card is on screen" — high enough that we never
  // start two videos mid-swipe, low enough to fire before the snap settles.
  var visibility = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
          play(entry.target);
        } else if (entry.target !== current) {
          pause(entry.target, false);
        }
      });
    },
    { root: feed, threshold: [0, 0.6, 1] }
  );

  function observe(reel) {
    visibility.observe(reel);
  }

  /* ------------------------------------------------------------ rendering */

  // Mirrors the Jinja markup in feed.html. Kept deliberately close to it so
  // a change in one is obvious in the other.
  function render(video) {
    var creator = video.creator || {};
    var handle = creator.handle || "";
    var price = creator.subscription_price_cents
      ? "Subscribe · $" + (creator.subscription_price_cents / 100).toFixed(2) + "/mo"
      : "Subscribe";

    var article = document.createElement("article");
    article.className = "reel";
    article.tabIndex = 0;
    article.dataset.videoId = video.video_id;

    var ctas = handle
      ? '<div class="reel-ctas">' +
        '<a class="btn btn-primary btn-sm" href="/' + handle + '/start-chat">Chat with ' + creator.display_name + "</a>" +
        '<a class="btn btn-glass btn-sm" href="/c/' + handle + '/subscribe">' + price + "</a>" +
        "</div>"
      : "";

    article.innerHTML =
      '<div class="reel-media">' +
        '<video class="reel-video" data-src="' + video.sources.mp4 + '" poster="' + video.poster_url + '"' +
        ' playsinline webkit-playsinline muted loop preload="none" disablepictureinpicture disableremoteplayback></video>' +
        '<div class="reel-scrim" aria-hidden="true"></div>' +
        '<button class="reel-tap" type="button" aria-label="Play or pause"></button>' +
        '<div class="reel-pausemark" aria-hidden="true"><svg viewBox="0 0 24 24" width="72" height="72"><path d="M8 5v14l11-7z" fill="currentColor"/></svg></div>' +
      "</div>" +
      '<div class="reel-overlay">' +
        '<div class="reel-info">' +
          '<a class="reel-creator" href="/c/' + handle + '">' +
            '<img class="reel-avatar" src="' + creator.avatar_url + '" alt="" width="44" height="44">' +
            '<span class="reel-names"><span class="reel-name">' + creator.display_name +
            ' <span class="verified">✔</span></span>' +
            (handle ? '<span class="reel-handle">@' + handle + "</span>" : "") +
          "</span></a>" +
          (video.caption ? '<p class="reel-caption">' + escapeHtml(video.caption) + "</p>" : "") +
          ctas +
        "</div>" +
        '<div class="reel-rail">' +
          '<a class="rail-btn rail-avatar" href="/c/' + handle + '" aria-label="View profile">' +
            '<img src="' + creator.avatar_url + '" alt="" width="46" height="46">' +
            '<span class="rail-follow" aria-hidden="true">+</span></a>' +
          '<button class="rail-btn js-like" type="button" aria-pressed="false" aria-label="Like" data-count="' + (video.like_count || 0) + '">' +
            '<svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="M12 21s-7.5-4.9-9.6-9A5.4 5.4 0 0 1 12 6.2 5.4 5.4 0 0 1 21.6 12c-2.1 4.1-9.6 9-9.6 9z" fill="currentColor"/></svg>' +
            '<span class="rail-count js-like-count">' + compact(video.like_count) + "</span></button>" +
          '<a class="rail-btn" href="/' + handle + '/start-chat" aria-label="Message">' +
            '<svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.1A8 8 0 1 1 21 12z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>' +
            '<span class="rail-count">Chat</span></a>' +
          '<button class="rail-btn js-share" type="button" aria-label="Share" data-url="/c/' + handle + '">' +
            '<svg viewBox="0 0 24 24" width="30" height="30" aria-hidden="true"><path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M12 3v13M12 3 7 8M12 3l5 5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>' +
            '<span class="rail-count">Share</span></button>' +
          '<button class="rail-btn js-mute" type="button" aria-label="Unmute">' +
            '<svg class="icon-muted" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zM16 9l5 6M21 9l-5 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' +
            '<svg class="icon-unmuted" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4zM16.5 8.5a5 5 0 0 1 0 7M19 6a8 8 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>' +
          "</button>" +
        "</div>" +
      "</div>";

    return article;
  }

  function escapeHtml(s) {
    var div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  /* --------------------------------------------------------------- paging */

  function endCard() {
    var el = document.createElement("article");
    el.className = "reel";
    el.innerHTML =
      '<div class="reel-overlay" style="align-items:center;justify-content:center;height:100%">' +
      '<div class="reel-info" style="text-align:center">' +
      '<p class="reel-caption" style="-webkit-line-clamp:none">That\'s everything for now.</p>' +
      '<div class="reel-ctas" style="justify-content:center">' +
      '<a class="btn btn-primary btn-sm" href="/tara/start-chat">Chat with Tara</a></div></div></div>';
    return el;
  }

  async function loadMore() {
    if (isLoading || feed.dataset.hasMore !== "1") return;
    isLoading = true;
    try {
      var url = "/api/v1/feed?cursor=" + encodeURIComponent(feed.dataset.nextCursor || "");
      var response = await fetch(url, { credentials: "same-origin" });

      if (response.status === 403) {
        // The consent cookie expired mid-session. Send them back through the
        // gate rather than silently showing nothing.
        window.location.href = "/";
        return;
      }
      if (!response.ok) throw new Error("feed " + response.status);

      var data = await response.json();
      (data.videos || []).forEach(function (video) {
        var reel = render(video);
        feed.insertBefore(reel, sentinel);
        observe(reel);
      });

      feed.dataset.nextCursor = data.next_cursor || "";
      feed.dataset.hasMore = data.has_more ? "1" : "0";
      if (!data.has_more) feed.insertBefore(endCard(), sentinel);
    } catch (e) {
      // Leave hasMore set so the next scroll retries — a transient CDN or
      // network blip shouldn't permanently end someone's feed.
      isLoading = false;
      return;
    }
    isLoading = false;
  }

  // Fire well before the user reaches the bottom, so the next video is
  // already buffered by the time they swipe to it.
  new IntersectionObserver(
    function (entries) {
      if (entries[0].isIntersecting) loadMore();
    },
    { root: feed, rootMargin: "1500px 0px" }
  ).observe(sentinel);

  // Belt and braces. IntersectionObserver stops recomputing whenever the
  // page produces no frames — a backgrounded tab, some in-app webviews, and
  // heavy throttling on low-end Android all do this. Running out of feed is
  // the one failure the funnel cannot absorb, so a plain scroll check backs
  // the observer up. Both call the same guarded loader, so a double trigger
  // is a no-op.
  feed.addEventListener(
    "scroll",
    function () {
      var remaining = feed.scrollHeight - feed.scrollTop - feed.clientHeight;
      if (remaining < 1500) loadMore();
    },
    { passive: true }
  );

  /* ------------------------------------------------------------ interaction */

  feed.addEventListener("click", function (event) {
    var reel = event.target.closest(".reel");
    if (!reel) return;

    if (event.target.closest(".js-mute")) {
      isUnmuted = !isUnmuted;
      app.classList.toggle("is-unmuted", isUnmuted);
      reels().forEach(function (r) {
        var v = r.querySelector(".reel-video");
        if (v) v.muted = !isUnmuted;
      });
      return;
    }

    var like = event.target.closest(".js-like");
    if (like) {
      // Optimistic and local. There is no like endpoint yet — the counter is
      // the interaction, and the real write lands with the engagement API.
      var pressed = like.getAttribute("aria-pressed") === "true";
      var base = Number(like.dataset.count) || 0;
      like.setAttribute("aria-pressed", pressed ? "false" : "true");
      like.querySelector(".js-like-count").textContent = compact(base + (pressed ? 0 : 1));
      return;
    }

    var share = event.target.closest(".js-share");
    if (share) {
      var link = window.location.origin + share.dataset.url;
      if (navigator.share) navigator.share({ url: link }).catch(function () {});
      else if (navigator.clipboard) navigator.clipboard.writeText(link);
      return;
    }

    if (event.target.closest(".reel-tap")) toggle(reel);
  });

  // Desktop: arrow keys and space, which is what people reach for when the
  // feed is in a window rather than under a thumb.
  document.addEventListener("keydown", function (event) {
    if (event.target.matches("input, textarea")) return;
    var all = reels();
    var index = current ? all.indexOf(current) : 0;

    if (event.key === "ArrowDown" || event.key === "PageDown") {
      event.preventDefault();
      if (all[index + 1]) all[index + 1].scrollIntoView({ behavior: "smooth" });
    } else if (event.key === "ArrowUp" || event.key === "PageUp") {
      event.preventDefault();
      if (all[index - 1]) all[index - 1].scrollIntoView({ behavior: "smooth" });
    } else if (event.key === " " && current) {
      event.preventDefault();
      toggle(current);
    } else if (event.key.toLowerCase() === "m") {
      var mute = current && current.querySelector(".js-mute");
      if (mute) mute.click();
    }
  });

  // A backgrounded tab should not keep streaming video.
  document.addEventListener("visibilitychange", function () {
    if (!current) return;
    if (document.hidden) pause(current, false);
    else {
      var video = current.querySelector(".reel-video");
      if (video && !current.classList.contains("is-paused")) video.play().catch(function () {});
    }
  });

  /* ----------------------------------------------------------------- start */

  reels().forEach(observe);
  buffer(0);
  if (reels()[0]) play(reels()[0]);
})();
