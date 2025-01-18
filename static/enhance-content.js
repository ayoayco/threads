class EnhanceContent extends HTMLElement {
  connectedCallback() {
    const el = this.getElementsByClassName("hashtag");
    const server = this.dataset.server;
    const tagUrl = this.dataset.tagUrl;

    for (let i = 0; i < el.length; i++) {
      const tagEl = el.item(i);
      const currentHref = tagEl.getAttribute("href");
      const tagName = currentHref.replace(`${server}/tags/`, "");
      tagEl.setAttribute("href", tagUrl + tagName);

      const parentEl = tagEl.parentElement;
      const siblings = parentEl.childNodes;
      let validSiblingsCount = 0;

      for (const sibling of siblings) {
        if (!(sibling.nodeType === 3 && sibling.textContent === " ")) {
          validSiblingsCount++;
        }
      }

      const childrenTags = parentEl.getElementsByClassName("hashtag");

      console.log({ childrenTags, siblings, validSiblingsCount });

      const isTagBar = validSiblingsCount === childrenTags.length;

      if (isTagBar) {
        tagEl.textContent = tagName;
        tagEl.classList.add("pill");
      }
    }
  }
}

customElements.define("enhance-content", EnhanceContent);
