const siteAboutDialog = document.querySelector("#about-dialog");
const openSiteAbout = () => siteAboutDialog.showModal();
const closeSiteAbout = () => siteAboutDialog.close();

document.querySelector("#about-open")?.addEventListener("click", openSiteAbout);
document.querySelector("#about-open-footer").addEventListener("click", openSiteAbout);
document.querySelector("#about-close").addEventListener("click", closeSiteAbout);
document.querySelector("#about-continue").addEventListener("click", closeSiteAbout);
siteAboutDialog.addEventListener("click", (event) => {
  if (event.target === siteAboutDialog) closeSiteAbout();
});
siteAboutDialog.addEventListener("close", () => {
  window.localStorage.setItem("skate-scores-about-seen", "true");
});
if (document.body.hasAttribute("data-show-welcome")
  && window.localStorage.getItem("skate-scores-about-seen") !== "true") {
  openSiteAbout();
}

const searchLink = document.querySelector('.topbar-nav a[href="#search"]');
const directoryLink = document.querySelector('.topbar-nav a[href="#directory"]');
const directorySection = document.querySelector("#directory");
if (searchLink && directoryLink && directorySection) {
  const updateCurrentSection = () => {
    const headerBottom = document.querySelector(".topbar").getBoundingClientRect().bottom;
    const inDirectory = directorySection.getBoundingClientRect().top <= headerBottom + 32;
    searchLink.toggleAttribute("aria-current", !inDirectory);
    directoryLink.toggleAttribute("aria-current", inDirectory);
    (inDirectory ? directoryLink : searchLink).setAttribute("aria-current", "location");
  };
  window.addEventListener("scroll", updateCurrentSection, { passive: true });
  window.addEventListener("resize", updateCurrentSection);
  window.addEventListener("load", updateCurrentSection);
  const sectionObserver = new ResizeObserver(updateCurrentSection);
  sectionObserver.observe(document.querySelector("main"));
  sectionObserver.observe(document.querySelector(".topbar"));
  updateCurrentSection();
}
