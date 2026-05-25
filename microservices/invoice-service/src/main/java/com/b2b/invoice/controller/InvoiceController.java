package com.b2b.invoice.controller;

import com.b2b.invoice.entity.Invoice;
import com.b2b.invoice.service.InvoiceService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/invoices")
public class InvoiceController {

    private final InvoiceService service;

    public InvoiceController(InvoiceService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Invoice create(@RequestBody Invoice invoice) {
        return service.create(invoice);
    }

    @GetMapping
    public List<Invoice> findAll() {
        return service.findAll();
    }

    @GetMapping("/{id}")
    public Invoice findById(@PathVariable Long id) {
        return service.findById(id);
    }

    @GetMapping("/partner/{partnerId}")
    public List<Invoice> findByPartner(@PathVariable Long partnerId) {
        return service.findByPartnerId(partnerId);
    }

    @PatchMapping("/{id}/status")
    public Invoice updateStatus(@PathVariable Long id, @RequestParam Invoice.InvoiceStatus status) {
        return service.updateStatus(id, status);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
