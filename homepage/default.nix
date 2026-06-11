{ runCommand, writeText, services ? [] }:

let
  servicesJson = writeText "services.json" (builtins.toJSON services);
in
runCommand "ishimura-homepage" {} ''
  mkdir -p $out
  cp ${./src/index.html}  $out/index.html
  cp ${./src/style.css}   $out/style.css
  cp ${./src/app.js}      $out/app.js
  cp ${./src/404.html}    $out/404.html
  cp ${servicesJson}      $out/services.json
''
