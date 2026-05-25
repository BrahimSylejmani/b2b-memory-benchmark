package com.b2b.monolith.partner.controller;

import com.b2b.monolith.partner.entity.Partner;
import com.b2b.monolith.partner.service.PartnerService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/partners")
public class PartnerController {

    private final PartnerService service;

    public PartnerController(PartnerService service) {
        this.service = service;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Partner create(@RequestBody Partner partner) {
        return service.create(partner);
    }

    @GetMapping
    public List<Partner> findAll() {
        return service.findAll();
    }

    @GetMapping("/{id}")
    public Partner findById(@PathVariable Long id) {
        return service.findById(id);
    }

    @PutMapping("/{id}")
    public Partner update(@PathVariable Long id, @RequestBody Partner partner) {
        return service.update(id, partner);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
