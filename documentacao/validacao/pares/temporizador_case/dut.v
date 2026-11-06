module top_module (
    input clk,
    input reset,      // Synchronous reset
    input data,
    output [3:0] count,
    output counting,
    output done,
    input ack
);

    localparam S_SEARCH0 = 4'd0;
    localparam S_SEARCH1 = 4'd1;
    localparam S_SEARCH11 = 4'd2;
    localparam S_SEARCH110 = 4'd3;
    localparam S_SHIFT = 4'd4;
    localparam S_COUNT = 4'd5;
    localparam S_DONE = 4'd6;

    reg [3:0] state;
    reg [3:0] delay_value;
    reg [3:0] remaining;
    reg [1:0] shift_count;
    reg [9:0] cycle_count;

    assign counting = (state == S_COUNT);
    assign done = (state == S_DONE);
    assign count = remaining;

    always @(posedge clk) begin
        if (reset) begin
            state <= S_SEARCH0;
            delay_value <= 4'd0;
            remaining <= 4'd0;
            shift_count <= 2'd0;
            cycle_count <= 10'd0;
        end else begin
            case (state)

                S_SEARCH0: begin
                    if (data)
                        state <= S_SEARCH1;
                    else
                        state <= S_SEARCH0;
                end

                S_SEARCH1: begin
                    if (data)
                        state <= S_SEARCH11;
                    else
                        state <= S_SEARCH0;
                end

                S_SEARCH11: begin
                    if (data)
                        state <= S_SEARCH11;
                    else
                        state <= S_SEARCH110;
                end

                S_SEARCH110: begin
                    if (data) begin
                        state <= S_SHIFT;
                        delay_value <= 4'd0;
                        shift_count <= 2'd0;
                    end else begin
                        state <= S_SEARCH0;
                    end
                end

                S_SHIFT: begin
                    delay_value <= {delay_value[2:0], data};

                    if (shift_count == 2'd3) begin
                        state <= S_COUNT;
                        remaining <= {delay_value[2:0], data};
                        cycle_count <= 10'd0;
                    end else begin
                        shift_count <= shift_count + 1'b1;
                    end
                end

                S_COUNT: begin
                    if (cycle_count == 10'd999) begin
                        cycle_count <= 10'd0;

                        if (remaining == 4'd0) begin
                            state <= S_DONE;
                        end else begin
                            remaining <= remaining - 1'b1;
                        end
                    end else begin
                        cycle_count <= cycle_count + 1'b1;
                    end
                end

                S_DONE: begin
                    if (ack) begin
                        state <= S_SEARCH0;
                        delay_value <= 4'd0;
                        remaining <= 4'd0;
                        shift_count <= 2'd0;
                        cycle_count <= 10'd0;
                    end else begin
                        state <= S_DONE;
                    end
                end

                default: begin
                    state <= S_SEARCH0;
                    delay_value <= 4'd0;
                    remaining <= 4'd0;
                    shift_count <= 2'd0;
                    cycle_count <= 10'd0;
                end

            endcase
        end
    end

endmodule
