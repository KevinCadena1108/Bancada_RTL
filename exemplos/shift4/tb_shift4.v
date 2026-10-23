// Testbench do Shift4 (HDLBits). Cobre reset assincrono, load, shift e prioridade.
module tb;
    reg        clk = 0, areset, load, ena;
    reg  [3:0] data;
    wire [3:0] q;
    integer    erros = 0;

    top_module dut (.clk(clk), .areset(areset), .load(load),
                    .ena(ena), .data(data), .q(q));

    always #5 clk = ~clk;
    task step; begin @(posedge clk); #1; end endtask

    initial begin
        // reset assincrono (sem borda de clock) deve zerar imediatamente
        areset = 1; load = 0; ena = 0; data = 4'b0000; #1;
        if (q !== 4'b0000) begin $display("ERRO: areset nao zerou (q=%b)", q); erros = erros + 1; end
        areset = 0;

        // load sincrono
        load = 1; data = 4'b1011; step;
        if (q !== 4'b1011) begin $display("ERRO: load (q=%b esp=1011)", q); erros = erros + 1; end

        // shift a direita: 1011 -> 0101 -> 0010
        load = 0; ena = 1; step;
        if (q !== 4'b0101) begin $display("ERRO: shift1 (q=%b esp=0101)", q); erros = erros + 1; end
        step;
        if (q !== 4'b0010) begin $display("ERRO: shift2 (q=%b esp=0010)", q); erros = erros + 1; end

        // ena=0 e load=0: segura o valor
        ena = 0; step;
        if (q !== 4'b0010) begin $display("ERRO: hold (q=%b esp=0010)", q); erros = erros + 1; end

        // load tem prioridade sobre ena
        load = 1; ena = 1; data = 4'b1111; step;
        if (q !== 4'b1111) begin $display("ERRO: prioridade load>ena (q=%b esp=1111)", q); erros = erros + 1; end

        // reset assincrono no meio da operacao
        areset = 1; #1;
        if (q !== 4'b0000) begin $display("ERRO: areset no meio (q=%b)", q); erros = erros + 1; end

        if (erros != 0) $fatal(1, "shift4: %0d erros", erros);
        $display("[PASSOU] shift4 ok");
        $finish;
    end
endmodule
