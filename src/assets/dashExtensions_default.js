window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, layer, context) {
            layer.bindTooltip(`KAD: ${feature.properties.KAD || 'No KAD available'} <br> ha: ${feature.properties.Hectares} <br> pag: ${feature.properties.pag}`)
        }

    }
});