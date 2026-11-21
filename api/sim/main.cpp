// Harness do Verilator: roda o loop de tempo ate o $finish e grava a cobertura.
// O testbench e' Verilog; o modulo do topo se chama sempre "tb".
// Uso: ./sim <arquivo_de_cobertura>

#include <memory>
#include <string>
#include <verilated.h>
#include "Vtb.h"
#if VM_COVERAGE
#include <verilated_cov.h>

// $fatal aborta o processo antes do fim do main, o que perderia a cobertura
// coletada ate ali. O Verilator roda os callbacks de flush antes de abortar,
// entao gravamos tambem por esse caminho.
static VerilatedContext* g_ctx = nullptr;
static std::string g_covfile = "coverage.dat";
static void gravar_cobertura(void*) {
    if (g_ctx) g_ctx->coveragep()->write(g_covfile.c_str());
}
#endif

int main(int argc, char** argv) {
    const std::unique_ptr<VerilatedContext> ctx{new VerilatedContext};
    ctx->commandArgs(argc, argv);
    const std::unique_ptr<Vtb> top{new Vtb{ctx.get()}};

#if VM_COVERAGE
    if (argc > 1) g_covfile = argv[1];
    g_ctx = ctx.get();
    Verilated::addFlushCb(gravar_cobertura, nullptr);
#endif

    while (!ctx->gotFinish()) {
        top->eval();
        if (!top->eventsPending()) break;
        ctx->time(top->nextTimeSlot());
    }
    top->final();

#if VM_COVERAGE
    gravar_cobertura(nullptr);
    Verilated::removeFlushCb(gravar_cobertura, nullptr);
    g_ctx = nullptr;
#endif
    return 0;
}
