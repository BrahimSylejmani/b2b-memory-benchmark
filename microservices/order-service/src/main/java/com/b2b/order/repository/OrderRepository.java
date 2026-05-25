package com.b2b.order.repository;

import com.b2b.order.entity.Order;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByPartnerId(Long partnerId);
}
