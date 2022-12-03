var nunjucksEnv = new nunjucks.Environment();

htmx.defineExtension('client-side-templates', {
    transformResponse : function(text, xhr, elt) {

        var nunjucksTemplate = htmx.closest(elt, "[nunjucks-template]");
        if (nunjucksTemplate) {
            var data = JSON.parse(text);
            var templateName = nunjucksTemplate.getAttribute('nunjucks-template');
            var template = htmx.find('#' + templateName);
            if (template) {
                return nunjucksEnv.renderString(template.innerHTML, data);
            } else {
                return nunjucksEnv.render(templateName, data);
            }
          }

        return text;
    }
});