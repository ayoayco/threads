import { WebComponent } from "web-component-base";

class EnhanceContent extends WebComponent {
  static props = {
    server: "",
    tagUrl: "",
  };

  onInit() {
    const el = this.getElementsByClassName("hashtag");
    const server = this.props.server;
    const tagUrl = this.props.tagUrl;

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

      const isTagBar = validSiblingsCount === childrenTags.length;

      if (isTagBar) {
        parentEl.classList.add("tag-bar");
        tagEl.textContent = tagName;
        tagEl.classList.add("pill");
      }
    }
  }

  get template() {
    return this.innerHtml;
  }
}

customElements.define("enhance-content", EnhanceContent);
