// Testbench do Mux2to1 (HDLBits). Exaustivo: 3 entradas -> 8 casos.
module tb;
    reg  a, b, sel;
    wire out;
    integer erros = 0;
    integer i;
    reg esperado;

    top_module dut (.a(a), .b(b), .sel(sel), .out(out));

    initial begin
        for (i = 0; i < 8; i = i + 1) begin
            {sel, a, b} = i[2:0];
            #1;
            esperado = sel ? b : a;
            if (out !== esperado) begin
                $display("ERRO: sel=%b a=%b b=%b out=%b esperado=%b", sel, a, b, out, esperado);
                erros = erros + 1;
            end
        end
        if (erros != 0) $fatal(1, "mux2to1: %0d erros", erros);
        $display("[PASSOU] mux2to1 ok");
        $finish;
    end
endmodule
