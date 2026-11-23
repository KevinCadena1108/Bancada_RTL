module seq_detector (
    input clk,
    input rst,
    input x,
    output y
);
    localparam A = 2'd0, B = 2'd1, C = 2'd2, D = 2'd3;
    reg [1:0] state;

    always @(posedge clk) begin
        if (rst)
            state <= A;
        else begin
            case (state)
                A: state <= x ? B : A;
                B: state <= x ? B : C;
                C: state <= x ? D : A;
                D: state <= x ? B : C;
                default: state <= A;
            endcase
        end
    end

    assign y = (state == D);
endmodule
