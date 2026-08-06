# Proyecto de ejemplo en español

Un proyecto cvloom se instala en un idioma y opera en él. Este directorio es el
mismo tipo de proyecto que [`../examples/`](../examples/) — datos, perfiles y
salida — con una sola diferencia estructural: declara `locale: es` en
`cvloom.yaml`.

```bash
cd examples-es
uv run cvloom build --all --public
uv run cvloom check --profile general
```

## Un proyecto, un idioma

cvloom no mantiene una fuente única multilingüe. No hay ficheros de traducción,
ni mapas `{en: …, es: …}` dentro de los datos, ni traducción automática: dos
idiomas son dos directorios de proyecto, que es exactamente lo que este
directorio y `../examples/` demuestran. El motivo está en la decisión F7 — el
requisito es *operar en* un idioma, no traducir entre idiomas, y cada mecanismo
de traducción cobra complejidad permanente al esquema, al linter, al export y al
análisis de palabras clave para servir a una necesidad que no existe.

Lo que aporta el pack de idioma (`cvloom/locales/es.yaml`) es lo que cvloom
pondría en inglés por su cuenta: el atributo `lang` del documento, los títulos de
sección por defecto, la palabra para una fecha abierta (`Actualidad`) y el
contacto de relleno de `--public`. El contenido lo escribes tú, en español.

## El linter también opera en español

`cvloom check` no se limita a traducir mensajes — la terminal sigue en inglés a
propósito. Lo que cambia son las reglas: los lexicones, los umbrales y, en tres
casos, la lógica.

- **wl-007 (primera persona)** no marca `Lideré la migración`. El español es una
  lengua de sujeto nulo, así que la conjugación *es* el estilo correcto; sólo el
  pronombre explícito (`yo`, `mi`, `mis`) es un defecto.
- **wl-001 (voz pasiva)** busca la pasiva refleja (`se implementó`), más
  frecuente en prosa profesional que la perifrástica y sin equivalente formal en
  inglés.
- **wl-013** pasa a ser consistencia de estilo: infinitivo, primera persona del
  pretérito o sintagma nominal son opciones válidas, y mezclarlas es el defecto
  real.
- **wl-016 (legibilidad)** no se ejecuta: Fernández Huerta e INFLESZ son índices
  de *facilidad* en otra escala, así que la banda 6–12 de Flesch-Kincaid no
  significa nada aquí. `check` lo dice al terminar, en lugar de dar por buena una
  ejecución que corrió menos reglas de las que parece.

Los datos de este ejemplo son ficticios.
