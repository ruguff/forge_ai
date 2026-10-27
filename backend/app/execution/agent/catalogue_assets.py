"""Small offline SVG product illustrations, generated as source assets."""
import html

SHAPES = {
    'pack': '<path d="M131 92Q130 51 180 51Q230 51 229 92" fill="none" stroke="#37443b" stroke-width="14"/><rect x="103" y="82" width="154" height="207" rx="45" fill="#68745c"/><path d="M103 129H257V159Q180 198 103 159Z" fill="#536146"/><rect x="127" y="204" width="106" height="64" rx="15" fill="#859075"/><path d="M143 97V191M217 97V191" stroke="#c6ad84" stroke-width="11"/><rect x="145" y="224" width="70" height="6" rx="3" fill="#4c5941"/>',
    'bottle': '<rect x="157" y="44" width="47" height="34" rx="10" fill="#363e39"/><path d="M148 76H212L226 111V269Q226 287 208 287H152Q134 287 134 269V111Z" fill="#b57653"/><rect x="141" y="123" width="15" height="133" rx="7" fill="#d49a76"/><path d="M159 171H201M165 181H195" stroke="#eee6d5" stroke-width="4"/><path d="M205 48Q239 45 232 81" fill="none" stroke="#363e39" stroke-width="8"/>',
    'lamp': '<path d="M148 75Q148 25 180 25Q212 25 212 75" fill="none" stroke="#424c40" stroke-width="8"/><path d="M140 89L124 135V245H236V135L220 89Z" fill="#ecce8d"/><path d="M140 89H220M124 245H236" stroke="#424c40" stroke-width="17"/><path d="M138 129V241M222 129V241" stroke="#69725c" stroke-width="10"/><path d="M155 158Q180 138 205 158V219Q180 238 155 219Z" fill="#fff1bf"/><rect x="119" y="254" width="122" height="30" rx="13" fill="#46503f"/>',
    'stool': '<path d="M111 148L228 287M248 148L132 287" stroke="#ac855c" stroke-width="16" stroke-linecap="round"/><path d="M120 143L232 143L248 182Q180 215 106 182Z" fill="#7a8065"/><path d="M120 143L106 182M232 143L248 182" stroke="#535d48" stroke-width="7"/><circle cx="180" cy="222" r="9" fill="#675640"/>',
    'tote': '<path d="M139 122V79Q139 47 180 47Q221 47 221 79V122" fill="none" stroke="#aa8c65" stroke-width="13"/><path d="M100 115H260L247 286H113Z" fill="#c7b18b"/><path d="M119 131L129 270M242 131L233 270" stroke="#e1cba6" stroke-width="8"/><path d="M152 197H208M161 210H199" stroke="#66715b" stroke-width="6"/><path d="M111 284H248" stroke="#ae936d" stroke-width="6"/>',
    'blanket': '<path d="M104 83L236 58L270 261L137 286Z" fill="#b47961"/><path d="M119 112L242 88M130 172L251 148M140 232L261 208" stroke="#ddc5a3" stroke-width="21"/><path d="M137 286L140 303M157 282L160 299M177 279L180 296M197 275L200 292M217 272L220 289M237 268L240 285M257 264L260 281" stroke="#aa6c54" stroke-width="6"/>',
}
SHAPES['pack-detail'] = SHAPES['pack']


def svg(asset):
    viewbox = '100 85 165 205' if asset == 'pack-detail' else '0 0 360 340'
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="'+viewbox+'" role="img">'
            '<title>'+html.escape(asset.title())+' illustration</title>'
            '<ellipse cx="180" cy="300" rx="101" ry="13" fill="#3d4939" opacity=".09"/>'
            +SHAPES[asset]+'</svg>')
