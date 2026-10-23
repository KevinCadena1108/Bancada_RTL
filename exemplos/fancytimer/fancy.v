// HDLBits - Exams/review2015_fancytimer
// FSM (detecta 1101) + Datapath (le 4 bits de atraso e conta regressivo).
module top_module (
    input        clk,
    input        reset,     // reset sincrono
    input        data,
    output [3:0] count,
    output       counting,
    output       done,
    input        ack
);
    localparam S=4'd0, S1=4'd1, S11=4'd2, S110=4'd3,
               B0=4'd4, B1=4'd5, B2=4'd6, B3=4'd7,
               RUN=4'd8, DN=4'd9;

    reg [3:0] state, next;
    reg [3:0] cnt;      // segundos restantes (saida count)
    reg [9:0] sub;      // subcontador 999..0 (mil ciclos por segundo)

    // ---- proximo estado: detecta 1101, le 4 bits, conta, espera ack ----
    always @(*) begin
        case (state)
            S:    next = data ? S1  : S;
            S1:   next = data ? S11 : S;
            S11:  next = data ? S11 : S110;
            S110: next = data ? B0  : S;   // 1101 detectado
            B0:   next = B1;
            B1:   next = B2;
            B2:   next = B3;
            B3:   next = RUN;
            RUN:  next = (cnt == 4'd0 && sub == 10'd0) ? DN : RUN;
            DN:   next = ack ? S : DN;
            default: next = S;
        endcase
    end

    always @(posedge clk) begin
        if (reset) state <= S;
        else       state <= next;
    end

    // ---- datapath: shift dos 4 bits de atraso (MSB primeiro) e contagem ----
    always @(posedge clk) begin
        case (state)
            B0: cnt[3] <= data;
            B1: cnt[2] <= data;
            B2: cnt[1] <= data;
            B3: begin cnt[0] <= data; sub <= 10'd999; end
            RUN: begin
                if (sub == 10'd0) begin
                    sub <= 10'd999;
                    cnt <= cnt - 4'd1;
                end else
                    sub <= sub - 10'd1;
            end
            default: ;
        endcase
    end

    assign count    = cnt;
    assign counting = (state == RUN);
    assign done     = (state == DN);
endmodule
