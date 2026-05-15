program FibonacciRecursivo;
uses
  Classes, SysUtils;

// Función recursiva de Fibonacci
function Fibonacci(n: Integer): LongInt;
begin
  if (n = 0) then
    Result := 0
  else if (n = 1) then
    Result := 1
  else
    // Llamada recursiva
    Result := Fibonacci(n - 1) + Fibonacci(n - 2);
end;

var
  n, i: Integer;

begin
  Write('Ingrese la cantidad de términos: ');
  ReadLn(n);
  
  WriteLn('Serie de Fibonacci (recursiva):');
  for i := 0 to n - 1 do
  begin
    Write(Fibonacci(i), ' ');
  end;
  WriteLn;
  
  ReadLn;
end.